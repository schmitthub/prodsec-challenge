# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Senior Product Security Engineer take-home (brief: `challenge/candidate-brief.md`). `app/` is a **deliberately vulnerable** FastAPI "records API". The deliverable is not a fixed app — it is CI that protects it, one custom detection rule for a class off-the-shelf scanners miss (broken access control / IDOR), a triage writeup, a remediation message, `challenge/ai-security-review.md`, and an AI-usage note.

**Do not patch seeded vulnerabilities in `app/` unless explicitly asked.** They are the subject of the exercise. Seeded issues (all intentional): IDOR in `GET /api/records/{record_id}` (`app/routes/records.py` — no owner check; compare `/notes` which has one), SQL string interpolation in `db.search_records`, SSRF in `POST /api/webhooks/vendor-preview`, `verify_exp: False` + hardcoded `JWT_SECRET` in `app/auth.py`, plaintext passwords in `db.USERS`, `repr(exc)` leaked by the global exception handler, fake secrets in `config/dev.py` and `helpers/fixture_secrets.py`.

Status tracker: `challenge/notes.md`. Deliverables still empty: `challenge/report.md`, `challenge/ai-usage.md`; `challenge/ai-security-review.md` is the provided template.

## Commands

Two dependency surfaces exist and must stay in sync: `requirements.txt` (what README/CI/Dockerfile install) and `pyproject.toml` + `uv.lock` (runtime pins + `dev` group tooling). Python 3.11.

```bash
uv sync                                        # runtime + dev group (ruff, bandit, semgrep, osv-scanner, prek)
uv run python -m unittest discover -s tests    # full suite (what CI runs)
uv run python -m unittest tests.test_records.RecordsApiTests.test_health_check   # single test
uv run uvicorn app.main:app --reload           # API on :8000, docs at /docs
docker build -t records-api . && docker run --rm -p 8000:8000 records-api

uv run ruff check --fix . && uv run ruff format .
uv run bandit -r app/ -c pyproject.toml
uv run semgrep scan --config p/python --config p/security-audit --config .semgrep/ --config p/owasp-top-ten --error
uv run osv-scanner scan source .
prek run --all-files                           # runs every hook in .pre-commit-config.yaml (prek = pre-commit runner)
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

- `pr.yml` (pull_request → main) and `main.yml` (push main) are thin callers of two reusable workflows: `security.yml` (semgrep SARIF → code scanning, gitleaks with `--baseline-path gitleaks-report.json`, dependency-review on PRs only) and `test.yml`. Permissions are declared per calling job — reusable workflows do not inherit workflow-level blocks.
- `release.yml` (push tag `v*`): `validate` (semver regex, tag must be ancestor of `origin/main`) → `build.yml` (reusable, `workflow_call`). Attestation identity is anchored to `build.yml`'s path — verify with `gh attestation verify <artifact> --owner schmitthub --signer-workflow schmitthub/prodsec-challenge/.github/workflows/build.yml`. `build` job needs `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write` (actions/attest@v4).
- `.semgrep/actions.yaml` — custom rule: `pull_request_target` + cache-capable action (cache-poisoning). Runs in both CI and the `semgrep-actions` pre-commit hook. The BAC/IDOR custom rule for the app is still to be written here.
- Semgrep version is pinned in two places that must match: the image digest in `security.yml` and the comment in `.pre-commit-config.yaml`.
- Actions are SHA-pinned with `# vX.Y.Z` comments; dependabot groups actions/pip/docker weekly.
- GitHub rulesets (immutable tags, trunk-based) are configured server-side, not in repo.

### Scaffolding copied from the clawker (Go) repo — not yet adapted

Treat these as known-wrong until fixed; don't "preserve" them:

- `security.yml` uses `--config p/golang` (should be `p/python` / `p/owasp-top-ten` like the pre-commit hook) and carries a duplicate `test` job already covered by `test.yml`.
- `build.yml` installs cosign + syft but has no build, SBOM, or sign steps, and attests `release-subjects/*` which nothing creates. Intended end state: build artifact(s) → `syft` SBOM → `cosign` keyless sign (Sigstore OIDC) → `actions/attest` provenance + SBOM attestation.
- `release.yml` comments mention goreleaser; `.syft.yaml` is clawker's (go-module cataloger, `source.name: clawker`); `.gitleaksignore` references Go test paths; `.semgrepignore` comments mention Go; `.claude/settings.local.json` references a nonexistent `.claude/hooks/go-commands.sh`.
- `.claude/docs/*.md` are clawker's architecture docs — irrelevant here, ignore.
- `gitleaks-report.json` baseline referenced by CI and pre-commit does not exist yet.

## Agent environment

Runs inside a clawker container with a path-scoped egress firewall (`.clawker.yaml`). The image ships only CPython 3.14; uv fetches the project's **3.11** and Serena's pyright launcher's **3.13** (`uvx -p 3.13`) on demand into `UV_PYTHON_INSTALL_DIR=/home/clawker/.local/share/uv/python` (set via `agent.env` — the stack's default dir is root-owned and not writable by the agent user; see schmitthub/clawker#506). `.venv` is tmpfs-masked per `.clawkerignore` — empty on every container start; run `uv sync` first.
