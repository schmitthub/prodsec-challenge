# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Senior Product Security Engineer take-home (brief: `challenge/candidate-brief.md`). `app/` is a **deliberately vulnerable** FastAPI "records API". The deliverable is not a fixed app — it is CI that protects it, one custom detection rule for a class off-the-shelf scanners miss (broken access control / IDOR), a triage writeup, a remediation message, `challenge/ai-security-review.md`, and an AI-usage note.

**Do not patch seeded vulnerabilities in `app/` unless explicitly asked.** They are the subject of the exercise. Seeded issues (all intentional): IDOR in `GET /api/records/{record_id}` (`app/routes/records.py` — no owner check; compare `/notes` which has one), SQL string interpolation in `db.search_records`, SSRF in `POST /api/webhooks/vendor-preview`, `verify_exp: False` + hardcoded `JWT_SECRET` in `app/auth.py`, plaintext passwords in `db.USERS`, `repr(exc)` leaked by the global exception handler, fake secrets in `config/dev.py` and `helpers/fixture_secrets.py`.

Status tracker: `challenge/notes.md`. Deliverables still empty: `challenge/report.md`, `challenge/ai-usage.md`; `challenge/ai-security-review.md` is the provided template.

## Commands

`pyproject.toml` (no `[build-system]`: uv treats the project as virtual, `uv sync` installs deps only — the service is run from source) + `uv.lock` are the dependency source of truth (resolved, transitive, hash-pinned; `dev` group is ruff only) — SBOM and osv read `uv.lock`. `requirements.txt` still exists because README/Dockerfile install from it; CI checks it never drifts from the lock, and retiring it is a triage-writeup recommendation. Security scanners are deliberately **not** uv deps — they run from pinned `rev`s in `.pre-commit-config.yaml` (prek-managed envs) so tool requirements can't constrain runtime pins. Python 3.11.

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

## CI / release layout (`.github/workflows/`)

- `pr.yml` (pull_request → main) and `main.yml` (push main) are thin callers of two reusable workflows; permissions are declared per calling job — reusable workflows do not inherit workflow-level blocks.
- `test.yml`: `setup-uv` + `uv sync --frozen`, ruff check/format, unit tests, and a drift check that every pin in `requirements.txt` exists identically in `uv.lock`.
- `security.yml` jobs and their gates:
  - `semgrep` — one run writes SARIF (→ Code scanning, all severities) and JSON; on PRs `--baseline-commit` limits findings to the PR's, and only `ERROR|HIGH|CRITICAL` fail (inline python gate). Main: upload only.
  - `gitleaks` — full history, `.gitleaks.toml` (adds `lab-vendor-api-key` rule) + baseline `gitleaks-report.json`; regenerate the baseline with `gitleaks git . --config .gitleaks.toml --redact --report-path gitleaks-report.json` (stored redacted — every scan that consumes it must pass `--redact`, which CI and the prek hook both do; gitleaks compares `Match`/`Secret` against the baseline only when redact is 0), don't use `.gitleaksignore` for it.
  - `image` — calls `image.yml` (reusable; input `release: false`). No registry anywhere — the docker-archive is the artifact. Jobs:
    - `build` — `docker build` → `docker save` into `$RUNNER_TEMP/image/records-api.tar`, `actions/cache` keyed `image-<sha>` (skips the build on a hit; tag runs read main's cache), image ID from the archive's `manifest.json`, `upload-artifact` `records-api-image` (1 day). Commented BuildKit SBOM/provenance attestation block lives here.
    - `scan` — `download-artifact` → `.github/actions/osv-image-scan` (local composite: checksum-verified osv-scanner 2.5.1, `scan image --archive` twice for SARIF + JSON, SARIF category `container`, jq gate fails on any finding with `max_severity` ≥ repo variable `CVSS_FAIL_THRESHOLD`, default 9.0).
    - `sign` — `if: inputs.release`, `needs: [build, scan]`: gzip to `records-api-<tag>.image.tar.gz`, `cosign sign-blob --bundle`, `actions/attest` provenance, self-verify against **`image.yml`'s** identity, upload `records-api-image-signed` (gz + bundle). Workflow outputs `image-id`, `signed-artifact`, `signed-archive`.
  - `osv` — official reusable workflow on `uv.lock` (`-L uv.lock`), report-only. `dependency-review` (PRs) fails on new High+ deps.
- `codeql.yml` (push main, PR → main, weekly): advanced setup, matrix `python` + `actions`, `config-file: .github/codeql/codeql-config.yml` (`security-and-quality` suite, `paths-ignore` for tests/challenge/agent dirs — no `paths:` allowlist, it would hide workflows from the `actions` analysis). Custom pack skeleton at `.github/codeql/custom-queries/` (`qlpack.yml` + compiling placeholder `challenge.ql`); its `- uses:` line in the config is commented out until a real query lands.
- `release.yml` (push tag `v*`): `validate` (semver regex, tag must be ancestor of `origin/main`) → `image` (image.yml with `release: true`: build → scan gate → sign) → `build.yml` (reusable, inputs `image-artifact`/`image-archive`/`image-id` from image.yml outputs): `git archive` of the tag → download the signed image set, copy the gz into `release-subjects/` → syft SPDX+CycloneDX SBOMs of `uv.lock` → `SHA256SUMS` (covers the image gz) → `cosign sign-blob` bundles for everything except the image gz, then copy in image.yml's bundle → `actions/attest` v4 (provenance mode over the source archive, SBOMs and SHA256SUMS — not the image, which image.yml attested; then SBOM mode with `sbom-path`) → self-verify (`gh attestation verify` and `cosign verify-blob` per file, identity `build.yml` or `image.yml`) → `gh release create`. The image is shipped only as a docker-archive (no registry push). Signing identity is anchored to `build.yml`'s path: `gh attestation verify <artifact> --owner schmitthub --signer-workflow schmitthub/prodsec-challenge/.github/workflows/build.yml`. `build` job needs `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`; the `image` job needs `security-events: write` plus, on releases, `id-token`/`attestations`/`artifact-metadata: write`.
- `.semgrep/actions.yaml` — custom rule: `pull_request_target` + cache-capable action (cache-poisoning). Runs in CI and the actions pre-commit hook. The BAC/IDOR custom rule for the app is still to be written here.
- Tool versions pinned in two places that must match: `security.yml` (semgrep image tag, `GITLEAKS_VERSION`) / `.github/actions/osv-image-scan/action.yml` (`OSV_SCANNER_VERSION`) and the `rev` of the corresponding hook in `.pre-commit-config.yaml`. Dependabot does not bump hook `rev`s — use `prek auto-update` when bumping CI.
- Actions are SHA-pinned with `# vX.Y.Z` comments; dependabot groups actions/pip/docker weekly.
- GitHub rulesets (immutable tags, trunk-based) are configured server-side, not in repo.
- `prek run --all-files` also runs ruff `--fix`/format and whitespace fixers over the seeded `app/`, `tests/`, `helpers/`, `README.md` and rewrites them — revert those (`git checkout -- app tests helpers README.md`) unless a formatting commit is intended.

## Agent environment

Runs inside a clawker container with a path-scoped egress firewall (`.clawker.yaml`). The image ships only CPython 3.14; uv fetches the project's **3.11** and Serena's pyright launcher's **3.13** (`uvx -p 3.13`) on demand into `UV_PYTHON_INSTALL_DIR=/home/clawker/.local/share/uv/python` (set via `agent.env` — the stack's default dir is root-owned and not writable by the agent user; see schmitthub/clawker#506). `.venv` is tmpfs-masked per `.clawkerignore` — empty on every container start; run `uv sync` first.
