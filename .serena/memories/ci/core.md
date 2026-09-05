# CI / release pipeline

## Callers
- `pr.yml` (PR → main) and `main.yml` (push main) call reusable `security.yml` + `test.yml`.
- Permissions are explicit on each calling job; reusable workflows cannot expand caller grants.
- PR runs are concurrency-cancelled by PR number; main runs are keyed by SHA and not cancelled.

## Tests
- `test.yml`: Postgres 17 service → Python 3.11 → `uv sync --frozen` → `scripts/prestart.sh` (wait/migrate/seed) → `scripts/tests-start.sh` (wait + coverage-backed pytest).

## Security
- Semgrep: pinned container; general rules write JSON+SARIF. Their PR baseline diff gates ERROR/HIGH/CRITICAL through `.github/scripts/semgrep_gate.py --report`; their main findings upload only. A separate step in that same job runs `semgrep_gate.py --contracts` on both PR/main: rule fixtures, full app/ authorization scan, and justified rule-specific suppression audit. Contract failures always block; accepted exceptions print. The existing local Semgrep hook runs the same full-tree contract pass before its general scan.
- Custom authorization rules check semantic policy/binding wiring and reviewed-directory boundaries, independent of asset inheritance, provider result types, and response schemas. PUBLIC and use_policy are ERROR findings. See `mem:design/access-control-deps` for contracts and remaining server-side merge requirements.
- Bandit: pinned pip install; full SARIF upload. PR base-report comparison gates only new HIGH; main uploads only.
- Gitleaks: checksum-verified pinned CLI; full-history scan with `.gitleaks.toml`, redacted `gitleaks-report.json` baseline, SARIF upload.
- Container image: reusable `image.yml` builds/caches/uploads one docker archive; local OSV composite scans/uploads SARIF in a `continue-on-error` job. Vulnerabilities, scanner errors, and upload errors are advisory.
- Dependency review: PR-only when caller input is true; added/changed High+ advisories fail and comment on failure.
- CodeQL: Python + Actions matrix on main/PR/weekly with `security-and-quality`; ignored documentation/test/agent paths are configured in `.github/codeql/codeql-config.yml`.

## Release
- `release.yml` on `v*`: validate semver and ancestry on `origin/main` → call `image.yml release=true` → call `build.yml`.
- Image sign job depends on build, not advisory scan; gzip archive receives Cosign keyless bundle + GitHub provenance and is self-verified against `image.yml` identity.
- `build.yml`: source archive + signed image set + SPDX/CycloneDX SBOMs from `uv.lock` + SHA256SUMS; signs non-image subjects, imports image bundle, attests, self-verifies, publishes GitHub release.
- No registry push; released image is a signed docker-archive.

## Pin invariants
- Semgrep `security.yml` tag/digest ↔ local hook dependency.
- Bandit/Gitleaks versions in `security.yml` ↔ hook revisions.
- OSV version in `.github/actions/osv-image-scan/action.yml` ↔ hook revision.
- Actions use immutable SHAs with version comments.
