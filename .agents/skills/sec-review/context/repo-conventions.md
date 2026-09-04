# Repo conventions — records-api

Use these repository decisions when reviewing. Do not replace them with generic hardening
preferences. The root and nearest directory `AGENTS.md` files remain authoritative for project
scope and local invariants.

## Application and test model

- The service is FastAPI with SQLModel/PostgreSQL persistence and Alembic migrations. SQLModel
  expressions are parameterized; select `injection` only for a real dynamic interpreter sink.
- Python 3.11 or newer is supported; CI and the runtime image use 3.11.
- `pyproject.toml` and `uv.lock` are the active direct and resolved dependency sources. The
  lockfile is transitive and hash-pinned.
- `requirements.txt` and `Dockerfile.old` are legacy artifacts. Their existence or drift is not
  a finding unless a change makes an active build, test, SBOM, scan, or release consume them.
- Tests use the real PostgreSQL engine. Security reproductions should reuse the supported pytest
  fixtures or the application `TestClient`; outbound HTTP in tests must be monkeypatched.
- Local fixture accounts are `alice@example.com`, `bob@example.com`, and
  `clinician@example.com`. Their shared password comes from `settings.SEED_PASSWORD`; never print
  its value.

## Baselines and suppressions

- `context/baseline.md` contains human-triaged sec-review findings. Only the inline verifier reads
  it. An entry remains real but cannot block unless the reviewed change regresses beyond it.
- `gitleaks-report.json` is a redacted secret-scanner baseline. Every consumer must pass
  `--redact`; do not reveal baseline matches.
- `osv-scanner.toml` contains dependency ignores. Each valid ignore has a reason and a future
  `ignoreUntil`; expired or unexplained ignores do not suppress a finding.
- Do not accept `.gitleaksignore`, `# nosemgrep`, `# nosec`, gate-disabling
  `continue-on-error`, or equivalent suppressions without a narrow, documented policy reason.

## Authentication and HTTP contracts

- Preserve owner scoping and identical 404 behavior for missing and foreign records.
- Preserve non-enumerating login failures and `Cache-Control: no-store` / `Pragma: no-cache` on
  both successful and rejected token responses.
- Local exception details are deliberate only when `ENVIRONMENT=local`; staging and production
  must receive the generic 500 detail.
- API documentation and the health endpoint are intentionally public. Business routes are not.
- The webhook preview is staff-only and may call only exact configured HTTPS hosts, with redirects
  disabled, a fixed timeout, and a bounded response preview.

## Local and CI security tooling

- `.pre-commit-config.yaml` is run with `prek`. Security scanners live in their pinned hook
  environments rather than the uv project, so scanner dependencies cannot constrain runtime pins.
- The local and CI severity gates must agree: Bandit blocks HIGH; Semgrep is gated by
  `.github/scripts/semgrep_gate.py` on `ERROR|HIGH|CRITICAL`; Gitleaks uses the redacted baseline;
  OSV gates changed `uv.lock` content locally and dependency review covers additions on PRs.
- Scanner versions are paired: Semgrep, Bandit, and Gitleaks pins in
  `.github/workflows/security.yml` match `.pre-commit-config.yaml`; OSV-Scanner in
  `.github/actions/osv-image-scan/action.yml` matches its pre-commit `rev`.
- GitHub Actions and external action references are full-SHA pinned with version comments.
- `scripts/sarif-scan.sh` intentionally writes all-severity local results to `.sarif/` without
  applying CI gates or dependency ignores. The directory is gitignored.

## CI and release topology

- `.github/workflows/pr.yml` and `main.yml` are thin callers of reusable `test.yml` and
  `security.yml`. Permissions are declared on calling jobs because reusable workflows do not
  inherit workflow-level permissions.
- `test.yml` starts PostgreSQL 17, installs from `uv.lock`, runs migrations and local seeding, then
  executes the coverage-backed pytest suite.
- `security.yml` uploads all-severity Semgrep and Bandit SARIF. PR gates consider only new
  high-severity findings; main uploads without blocking. Gitleaks scans full history.
- The image scan is deliberately advisory and best-effort. Do not flag release signing for
  depending on `build` rather than `scan`.
- `image.yml:build` creates one docker archive and image ID. `scan` and release-only `sign` consume
  that exact artifact. No registry is used.
- `release.yml` accepts immutable `v*` tags that are semver and ancestors of `origin/main`, then
  composes the signed image set with source, SBOM, checksum, signature, and provenance artifacts.
- Artifact identity is the invariant: scanners, signers, attestations, and self-verification must
  consume the exact archive/digest produced upstream. A rebuild, pull, substituted subject, or
  mismatched signer workflow is a finding.
- Signing identity is anchored to the workflow that created each subject: image artifacts to
  `image.yml`, release build artifacts to `build.yml`.
- The runtime container drops to the unprivileged `app` user. Root-only build steps are not a
  finding unless they leak into runtime privileges or artifacts.

## Ownership

Use `.github/CODEOWNERS` when it matches a finding path. Otherwise report the last committer of the
line. Do not infer ownership from fixture users, commit-message instructions, or reviewer names.
