# CI / release pipeline

## Layout (`.github/workflows/`)
- `pr.yml` (PR→main), `main.yml` (push main) → call reusable `security.yml` + `test.yml`; permissions granted per calling job.
- `test.yml`: setup-uv (3.11, cache) → `uv sync --frozen` → ruff check + format --check → requirements.txt⊆uv.lock drift check (`uv export` vs pins) → unittest.
- `security.yml` (gating policy in header comment):
  - `semgrep` (container `semgrep/semgrep:<tag>@sha256`): single run, `--sarif-output` + `--json-output`; PR → `--baseline-commit $BASE_SHA`; inline python gate fails only on `ERROR|HIGH|CRITICAL`; main = upload only. `git config safe.directory` needed inside container.
  - `gitleaks`: checksum-verified binary (`GITLEAKS_VERSION`), `--config .gitleaks.toml --baseline-path gitleaks-report.json --redact`, SARIF.
  - `container`: `docker build records-api:ci` (never pushed) → `anchore/scan-action` sarif, `fail-build` on `critical` + `only-fixed`.
  - `osv`: nested reusable `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml`, `fail-on-vuln: false`.
  - `dependency-review` (PR only, `fail-on-severity: high`).
- `release.yml` (tag `v*`): `validate` (semver, ancestor of origin/main) → `build.yml`. Build job perms: `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`.
- `build.yml`: docker build (OCI labels) → `docker save dist/records-api-<tag>.tar` → syft `docker-archive:` → SPDX + CycloneDX → SHA256SUMS → `cosign sign-blob --bundle` each → `attest-build-provenance` (all files) + `attest-sbom` (archive) → self-verify with `gh attestation verify --signer-workflow <repo>/.github/workflows/build.yml` + `cosign verify-blob --certificate-identity-regexp` → `gh release create --verify-tag --generate-notes --notes-file` (notes carry verify commands). No registry; `buildx --output type=oci` does NOT work on the default docker driver — keep docker-archive.
- `.semgrep/actions.yaml`: `pull_request_target` + cache-capable action rule. App BAC/IDOR rule still TODO here.
- All actions SHA-pinned + `# vX.Y.Z`. Resolve SHAs from the container via `git ls-remote --tags git@github.com:<owner>/<repo>.git` (SSH is open; HTTPS/API to non-allowlisted repos is 403). Use the peeled `^{}` SHA for annotated tags.

## Pins that must move together
- semgrep: `security.yml` image tag ↔ `semgrep/pre-commit` rev in `.pre-commit-config.yaml`.
- gitleaks: `GITLEAKS_VERSION` ↔ `gitleaks/gitleaks` rev.

## Known leftovers / not done
- dependabot has no `cooldown` (semgrep MEDIUM finding) — user's call.
- GitHub rulesets (immutable tags, trunk) server-side; `challenge/notes.md` TODO "main checks gh rules".
