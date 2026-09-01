# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Senior Product Security Engineer take-home (brief: `challenge/candidate-brief.md`). `app/` is a **deliberately vulnerable** FastAPI "records API". The deliverable is not a fixed app — it is CI that protects it, one custom detection rule for a class off-the-shelf scanners miss (broken access control / IDOR), a triage writeup, a remediation message, `challenge/ai-security-review.md`, and an AI-usage note.

**Do not patch seeded vulnerabilities in `app/` unless explicitly asked.** They are the subject of the exercise. Seeded issues (all intentional): IDOR in `GET /api/records/{record_id}` (`app/routes/records.py` — no owner check; compare `/notes` which has one), SQL string interpolation in `db.search_records`, SSRF in `POST /api/webhooks/vendor-preview`, `verify_exp: False` + hardcoded `JWT_SECRET` in `app/auth.py`, plaintext passwords in `db.USERS`, `repr(exc)` leaked by the global exception handler, fake secrets in `config/dev.py` and `helpers/fixture_secrets.py`.

Status tracker: `challenge/notes.md`. Deliverables still empty: `challenge/report.md`, `challenge/ai-usage.md`; `challenge/ai-security-review.md` is the provided template.

## Commands

`pyproject.toml` + `uv.lock` are the dependency source of truth (resolved, transitive, hash-pinned; `dev` group is ruff only) — SBOM and osv read `uv.lock`. `requirements.txt` still exists because README/Dockerfile install from it; CI checks it never drifts from the lock, and retiring it is a triage-writeup recommendation. Security scanners are deliberately **not** uv deps — they run from pinned `rev`s in `.pre-commit-config.yaml` (prek-managed envs) so tool requirements can't constrain runtime pins. Python 3.11.

```bash
uv sync                                        # runtime + dev group (ruff only; scanners live in pre-commit)
uv run python -m unittest discover -s tests    # full suite (what CI runs)
uv run python -m unittest tests.test_records.RecordsApiTests.test_health_check   # single test
uv run uvicorn app.main:app --reload           # API on :8000, docs at /docs
docker build -t records-api . && docker run --rm -p 8000:8000 records-api

uv run ruff check --fix . && uv run ruff format .
prek run --all-files                           # ruff, gitleaks, bandit, semgrep (python + actions), osv-scanner — each from its pinned rev in prek's cache
prek run semgrep --all-files                   # one hook by id
```

Test accounts: `alice@example.test`/`alice-password`, `bob@example.test`/`bob-password` (members), `clinician@example.test`/`clinician-password` (staff). Login `POST /api/login` → bearer token.

Commit guard: `.claude/hooks/git-checks.sh` blocks `--no-verify`, `-n`, `SKIP=`, `core.hooksPath` overrides, and plumbing commits. Pre-commit hooks always run; don't route around them. `.codex/hooks/hooks.json` mirrors this for Codex.

## App architecture

- `app/main.py` — `FastAPI` app, mounts four routers under `/api`, `/health`, catch-all exception handler.
- `app/auth.py` — HS256 JWT issue/verify; `get_current_user` is the auth dependency every protected route takes via `Annotated[User, Depends(get_current_user)]`. There is no authorization layer — each route does (or fails to do) its own ownership/role check.
- `app/db.py` — no real database. `USERS`/`RECORDS` dicts; `search_records` builds a throwaway in-memory sqlite per call.
- `app/routes/` — `login`, `records` (`/me`, `/records`, `/records/{id}`, `/records/{id}/notes`), `search` (`/search?q=`), `webhooks` (staff-only outbound GET to caller-supplied URL).
- `app/models.py` — `User`, `TokenResponse` pydantic models.
- `tests/test_records.py` — `unittest` + `fastapi.testclient`; module-level `login()`/`auth_headers()` helpers. Only happy paths are covered; no negative-authz tests.
- `src/prodsec_challenge/` — uv scaffold stub, not part of the service.

## CI / release layout (`.github/workflows/`)

- `pr.yml` (pull_request → main) and `main.yml` (push main) are thin callers of two reusable workflows; permissions are declared per calling job — reusable workflows do not inherit workflow-level blocks.
- `test.yml`: `setup-uv` + `uv sync --frozen`, ruff check/format, unit tests, and a drift check that every pin in `requirements.txt` exists identically in `uv.lock`.
- `security.yml` jobs and their gates:
  - `semgrep` — one run writes SARIF (→ Code scanning, all severities) and JSON; on PRs `--baseline-commit` limits findings to the PR's, and only `ERROR|HIGH|CRITICAL` fail (inline python gate). Main: upload only.
  - `gitleaks` — full history, `.gitleaks.toml` (adds `lab-vendor-api-key` rule) + baseline `gitleaks-report.json`; regenerate the baseline with `gitleaks git . --report-path gitleaks-report.json`, don't use `.gitleaksignore` for it.
  - `container` — `docker build` → push to a job-local `registry:3` service → grype scans by digest (`anchore/scan-action`), fails on Critical with a fix available; SARIF category `container`. A commented block shows the BuildKit SBOM/provenance attestation flow that a real registry would get. The Dockerfile is local-dev only, not a release artifact.
  - `osv` — official reusable workflow on `uv.lock` (`-L uv.lock`), report-only. `dependency-review` (PRs) fails on new High+ deps.
- `release.yml` (push tag `v*`): `validate` (semver regex, tag must be ancestor of `origin/main`) → `build.yml` (reusable): `git archive` of the tag → syft SPDX+CycloneDX SBOMs of `uv.lock` → `SHA256SUMS` → `cosign sign-blob` bundles → `actions/attest` v4 (provenance mode over `release-subjects/*`, then SBOM mode with `sbom-path`) → self-verify (`gh attestation verify`, `cosign verify-blob`) → `gh release create`. No Docker in releases; the service is deployed from source. Signing identity is anchored to `build.yml`'s path: `gh attestation verify <artifact> --owner schmitthub --signer-workflow schmitthub/prodsec-challenge/.github/workflows/build.yml`. `build` job needs `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`.
- `.semgrep/actions.yaml` — custom rule: `pull_request_target` + cache-capable action (cache-poisoning). Runs in CI and the actions pre-commit hook. The BAC/IDOR custom rule for the app is still to be written here.
- Tool versions pinned in two places that must match: `security.yml` (semgrep image tag, `GITLEAKS_VERSION`) and the `rev` of the corresponding hook in `.pre-commit-config.yaml`. Dependabot does not bump hook `rev`s — use `prek auto-update` when bumping CI.
- Actions are SHA-pinned with `# vX.Y.Z` comments; dependabot groups actions/pip/docker weekly.
- GitHub rulesets (immutable tags, trunk-based) are configured server-side, not in repo.
- `prek run --all-files` also runs ruff `--fix`/format and whitespace fixers over the seeded `app/`, `tests/`, `helpers/`, `README.md` and rewrites them — revert those (`git checkout -- app tests helpers README.md`) unless a formatting commit is intended.

## Agent environment

Runs inside a clawker container with a path-scoped egress firewall (`.clawker.yaml`). The image ships only CPython 3.14; uv fetches the project's **3.11** and Serena's pyright launcher's **3.13** (`uvx -p 3.13`) on demand into `UV_PYTHON_INSTALL_DIR=/home/clawker/.local/share/uv/python` (set via `agent.env` — the stack's default dir is root-owned and not writable by the agent user; see schmitthub/clawker#506). `.venv` is tmpfs-masked per `.clawkerignore` — empty on every container start; run `uv sync` first.
