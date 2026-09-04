# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This repository began as a Senior Product Security Engineer take-home and now contains a Postgres-backed FastAPI records service plus its security-focused CI and release pipeline. The current application uses SQLModel persistence, Alembic migrations, hashed passwords, expiring JWTs, owner-scoped record queries, and an allowlisted webhook fetcher.

Treat security behavior as deliberate. Do not weaken or broadly refactor authentication, authorization, query construction, outbound-request controls, or error handling unless the task explicitly calls for it. Keep authorization failures for foreign records indistinguishable from missing records (`404`).

## Scenario Boundary (Non-negotiable)

The `challenge/` directory contains scenario instructions and submission material; it is **not part of the project**. No application code, tests, scripts, CI workflows, configuration, scanner policy, or agent skill may import, parse, copy, link to, cite, name, or otherwise depend on anything under `challenge/`. Never use that directory as a runtime input, policy source, baseline, suppression justification, or project documentation target. If project tooling needs equivalent information, place it in an appropriate project-owned location outside `challenge/`.

The only permitted acknowledgement of `challenge/` outside that directory is this agent-instruction boundary and direct work on the scenario material when the user explicitly requests it. References from project artifacts into `challenge/` are always defects; remove the dependency rather than correcting its path.

## Commands

`pyproject.toml` + `uv.lock` are the dependency source of truth (resolved, transitive, hash-pinned). The dev group contains coverage, mypy, pytest, and ruff. `requirements.txt` and `Dockerfile.old` are legacy artifacts; current local, container, CI, SBOM, and OSV workflows use the uv project and lock. Security scanners are deliberately **not** uv dependencies — they run from pinned `rev`s in `.pre-commit-config.yaml` (prek-managed environments) so tool requirements cannot constrain runtime pins. Python 3.11 or newer is supported; CI and the image use 3.11.

```bash
uv sync --frozen                               # runtime + dev dependencies
docker compose up -d db                        # tests and app use real Postgres
uv run bash scripts/prestart.sh                # wait for DB, migrate, seed local fixtures
uv run pytest tests                            # full suite (what CI runs)
uv run pytest tests/api/routes/test_records.py # one module
uv run fastapi dev app/main.py                 # API on :8000, docs at /docs
docker compose up --build                      # Postgres + prestart + API (+ Adminer/Traefik wiring)

uv run bash scripts/lint.sh                     # mypy + ruff check/format check for app
uv run bash scripts/format.sh                   # ruff fix/format for app and scripts
prek run --all-files                           # ruff, gitleaks, bandit, semgrep (python + actions), osv-scanner, unit tests — scanners from their pinned rev in prek's cache; severity gates match CI (bandit HIGH; semgrep via the shared gate script)
prek run semgrep --all-files                   # one hook by id
scripts/sarif-scan.sh                         # full-tree SARIF for every scanner into .sarif/ (gitignored; VS Code SARIF Viewer auto-loads it) — all severities, baselines/gates not applied
```

Local seed accounts are `alice@example.com`, `bob@example.com` (members), and `clinician@example.com` (staff); all use `SEED_PASSWORD`. Login is OAuth2 password grant: form-encode `username=<email>&password=<SEED_PASSWORD>` to `POST /api/login` and use the returned bearer token.

Commit guard: `.claude/hooks/git-checks.sh` blocks `--no-verify`, `-n`, `SKIP=`, `core.hooksPath` overrides, and plumbing commits. Pre-commit hooks always run; don't route around them. `.codex/hooks/hooks.json` mirrors this for Codex.

## App architecture

- `app/main.py` — constructs the `FastAPI` application, configures CORS, mounts the versioned API router at `settings.API_V1_STR`, exposes `/health`, and handles otherwise-unhandled exceptions.
- `app/api/deps.py` — shared SQLModel session, bearer-token decoding, current-user/staff dependencies, and the currently unused `RecordDep` bearer alias.
- `app/api/main.py` and `app/api/routes/` — router composition plus login, current-user, owner-scoped records/search, record notes, and staff-only webhook preview endpoints.
- `app/core/config.py` — environment-backed `Settings`, CORS/host parsing, Postgres URL construction, and non-local secret validation.
- `app/core/db.py` — SQLModel engine plus idempotent local fixture seeding; schema changes belong in `app/alembic/`.
- `app/core/security.py` — HS256 access-token creation and bcrypt password hashing/verification.
- `app/models.py` — SQLModel table models, relationships, enums, request models, public response models, and token models.
- `app/crud.py` — user authentication/creation and record/note creation helpers.
- `tests/` — pytest coverage for API behavior, access-control invariants, CRUD/security helpers, and database pre-start probes; tests use the real Postgres engine.

## Agent documentation

Every source-bearing directory under `app/`, `scripts/`, and `tests/` owns an `AGENTS.md` describing that directory's role, direct files, and code symbols. Its sibling `CLAUDE.md` must be a portable relative symlink to `AGENTS.md`. Parent guides summarize child directories; the closest guide owns the exhaustive inventory for its direct files. Keep these guides and aliases synchronized whenever files or symbols move.

## CI / release layout (`.github/workflows/`)

- `pr.yml` (pull_request → main) and `main.yml` (push main) are thin callers of two reusable workflows; permissions are declared per calling job — reusable workflows do not inherit workflow-level blocks.
- `test.yml`: reusable pytest workflow with a Postgres 17 service. It installs from `uv.lock`, runs migrations/local seeding through `scripts/prestart.sh`, then executes the coverage-backed suite through `scripts/tests-start.sh`.
- `security.yml` jobs and their gates:
  - `semgrep` — one run writes SARIF (→ Code scanning, all severities) and JSON; on PRs `--baseline-commit` limits findings to the PR's, and only `ERROR|HIGH|CRITICAL` fail via `.github/scripts/semgrep_gate.py` — the same script the local semgrep hook runs (one hook, same config list as CI — semgrep scopes rules by language itself) (`--report` mode in CI, run-then-gate locally), because semgrep's `--severity` only knows INFO/WARNING/ERROR and drops HIGH/CRITICAL rules, and `semgrep ci` gates on `dev.semgrep.actions` metadata, not severity. Main: upload only.
  - `bandit` — `bandit[toml,sarif]==BANDIT_VERSION` via pip, full-tree SARIF (→ Code scanning, category `bandit`); on PRs a JSON scan of `git archive <base>` feeds `bandit -b` and only new HIGH findings fail. Main: upload only.
  - `gitleaks` — full history, `.gitleaks.toml` (adds `lab-vendor-api-key` rule) + baseline `gitleaks-report.json`; regenerate the baseline with `gitleaks git . --config .gitleaks.toml --redact --report-path gitleaks-report.json` (stored redacted — every scan that consumes it must pass `--redact`, which CI and the prek hook both do; gitleaks compares `Match`/`Secret` against the baseline only when redact is 0), don't use `.gitleaksignore` for it.
  - `image` — calls `image.yml` (reusable; input `release: false`). No registry anywhere — the docker-archive is the artifact. Jobs:
    - `build` — `docker build` → `docker save` into `$RUNNER_TEMP/image/records-api.tar`, `actions/cache` keyed `image-<sha>` (skips the build on a hit; tag runs read main's cache), image ID from the archive's `manifest.json`, `upload-artifact` `records-api-image` (1 day). Commented BuildKit SBOM/provenance attestation block lives here.
    - `scan` — `download-artifact` → `.github/actions/osv-image-scan` (local composite: checksum-verified osv-scanner 2.5.1, one `scan image --archive` SARIF scan, uploads all findings under category `container`; the entire job is best-effort and cannot block on vulnerabilities, scanner errors, or upload errors).
    - `sign` — `if: inputs.release`, `needs: build` (independent of the advisory scan): gzip to `records-api-<tag>.image.tar.gz`, `cosign sign-blob --bundle`, `actions/attest` provenance, self-verify against **`image.yml`'s** identity, upload `records-api-image-signed` (gz + bundle). Workflow outputs `image-id`, `signed-artifact`, `signed-archive`.
  - `dependency-review` (PRs) — diffs the dependency graph against base, fails on added/changed deps with High+ advisories. No separate lockfile scan job: existing pins are covered by the image scan and Dependabot alerts; the osv-scanner pre-commit hook gates `uv.lock` changes locally.
- `codeql.yml` (push main, PR → main, weekly): advanced setup, matrix `python` + `actions`, `config-file: .github/codeql/codeql-config.yml` (`security-and-quality` suite, `paths-ignore` for tests/challenge/agent dirs — no `paths:` allowlist, which would hide workflows from the `actions` analysis). Custom pack skeleton lives at `.github/codeql/custom-queries/`; its `- uses:` line remains commented out until a real query lands.
- `release.yml` (push tag `v*`): `validate` (semver regex, tag must be ancestor of `origin/main`) → `image` (image.yml with `release: true`: build → best-effort scan + sign) → `build.yml` (reusable, inputs `image-artifact`/`image-archive`/`image-id` from image.yml outputs): `git archive` of the tag → download the signed image set, copy the gz into `release-subjects/` → syft SPDX+CycloneDX SBOMs of `uv.lock` → `SHA256SUMS` (covers the image gz) → `cosign sign-blob` bundles for everything except the image gz, then copy in image.yml's bundle → `actions/attest` v4 (provenance mode over the source archive, SBOMs and SHA256SUMS — not the image, which image.yml attested; then SBOM mode with `sbom-path`) → self-verify (`gh attestation verify` and `cosign verify-blob` per file, identity `build.yml` or `image.yml`) → `gh release create`. The image is shipped only as a docker-archive (no registry push). Signing identity is anchored to `build.yml`'s path: `gh attestation verify <artifact> --owner schmitthub --signer-workflow schmitthub/prodsec-challenge/.github/workflows/build.yml`. `build` job needs `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`; the `image` job needs `security-events: write` plus, on releases, `id-token`/`attestations`/`artifact-metadata: write`.
- Tool versions pinned in two places that must match: `security.yml` (semgrep image tag, `BANDIT_VERSION`, `GITLEAKS_VERSION`) / `.github/actions/osv-image-scan/action.yml` (`OSV_SCANNER_VERSION`) and the corresponding pin in `.pre-commit-config.yaml` (hook `rev`, or `additional_dependencies` for the local semgrep hook). Dependabot bumps neither — `prek auto-update` for `rev`s, edit the semgrep pin by hand.
- Actions are SHA-pinned with `# vX.Y.Z` comments; dependabot groups actions/pip/docker weekly.
- GitHub rulesets (immutable tags, trunk-based) are configured server-side, not in repo.
- `prek run --all-files` includes fix-capable ruff and whitespace hooks plus the compose-backed pytest hook. Review formatter edits before committing and ensure Docker/Compose is available when app or test Python changes trigger pytest.

## Agent environment

Runs inside a clawker container with a path-scoped egress firewall (`.clawker.yaml`). The image ships only CPython 3.14; uv fetches the project's **3.11** and Serena's pyright launcher's **3.13** (`uvx -p 3.13`) on demand into `UV_PYTHON_INSTALL_DIR=/home/clawker/.local/share/uv/python` (set via `agent.env` — the stack's default dir is root-owned and not writable by the agent user; see schmitthub/clawker#506). `.venv` is tmpfs-masked per `.clawkerignore` — empty on every container start; run `uv sync` first.
