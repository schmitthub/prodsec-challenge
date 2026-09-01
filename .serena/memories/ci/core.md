# CI / release pipeline

## Layout (`.github/workflows/`)
- `pr.yml` (PR→main), `main.yml` (push main) → call reusable `security.yml` + `test.yml`; permissions granted per calling job.
- `test.yml`: setup-uv (3.11, cache) → `uv sync --frozen` → ruff check + format --check → requirements.txt⊆uv.lock drift check (`uv export` vs pins) → unittest.
- `security.yml` (gating policy in header comment):
  - `semgrep` (container `semgrep/semgrep:<tag>@sha256`): single run, `--sarif-output` + `--json-output`; PR → `--baseline-commit $BASE_SHA`; inline python gate fails only on `ERROR|HIGH|CRITICAL`; main = upload only. `git config safe.directory` needed inside container.
  - `gitleaks`: checksum-verified binary (`GITLEAKS_VERSION`), `--config .gitleaks.toml --baseline-path gitleaks-report.json --redact`, SARIF.
  - `image`: `uses: ./.github/workflows/image.yml` (reusable; input `release` bool, default false). Jobs: `build` (checkout → `actions/cache@55cc834… v6.1.0` path `$RUNNER_TEMP/image/records-api.tar` key `image-${{ github.sha }}` → `docker build`+`docker save` if miss → image ID via `tar -xOf … manifest.json | jq` → `upload-artifact@043fb46… v7.0.1` `records-api-image`; outputs artifact/archive/image-id); `scan` (needs build; checkout → `download-artifact@3e5f45b… v8.0.1` → `./.github/actions/osv-image-scan` composite: osv-scanner 2.5.1 checksum-verified → `scan image --archive` sarif + json → upload-sarif `category: container` → jq gate `groups[].max_severity >= ${{ vars.CVSS_FAIL_THRESHOLD }}` default 9.0); `sign` (`if: inputs.release`, needs [build, scan]; cosign-installer → download → gzip `records-api-<tag>.image.tar.gz` → `cosign sign-blob --bundle` → `actions/attest` provenance → self-verify vs image.yml identity → upload `records-api-image-signed`). Workflow outputs `image-id`, `signed-artifact`, `signed-archive`. release.yml: validate → image (`release: true`; perms incl. id-token/attestations/artifact-metadata write) → build.yml (downloads signed set; gz into release-subjects before SHA256SUMS; sign loop skips it; bundle copied in after; attest subject-path = source archive + sbom jsons + SHA256SUMS; verify per-file identity build/image). No registry. Commented BuildKit attestation block lives in image.yml build job.
  - `osv`: nested reusable `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml`, `scan-args: -L uv.lock`, `fail-on-vuln: false`.
  - `dependency-review` (PR only, `fail-on-severity: high`).
- `release.yml` (tag `v*`): `validate` (semver, ancestor of origin/main) → `build.yml`. Build job perms: `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`.
- `build.yml`: outputs go in `release-subjects/` (user's convention). No Docker. `git archive --prefix records-api-<tag>/` of the tag → `syft scan file:uv.lock` (SPDX + CycloneDX, 24 pkgs incl. transitives + dev ruff; `.syft.yaml` = source name only) → SHA256SUMS → `cosign sign-blob --bundle` each → `actions/attest@v4` twice: provenance mode (`subject-path: release-subjects/*`) and SBOM mode (`sbom-path`, subject = archive) — NOT the deprecated attest-build-provenance/attest-sbom wrappers → self-verify (`gh attestation verify --signer-workflow <repo>/.github/workflows/build.yml`, `cosign verify-blob --certificate-identity-regexp`) → `gh release create --verify-tag --generate-notes --notes-file`. Note: the uv wheel only packages `src/` stub, hence source archive not sdist/wheel.
- `.semgrep/actions.yaml`: `pull_request_target` + cache-capable action rule. App BAC/IDOR rule still TODO here.
- All actions SHA-pinned + `# vX.Y.Z`. Resolve SHAs from the container via `git ls-remote --tags git@github.com:<owner>/<repo>.git` (SSH open; HTTPS/API to non-allowlisted repos is 403). Use the peeled `^{}` SHA for annotated tags. Docker Hub digests: `docker pull` + `docker inspect --format '{{index .RepoDigests 0}}'` (daemon has host network).

## Pins that must move together
- semgrep: `security.yml` image tag ↔ `semgrep/pre-commit` rev in `.pre-commit-config.yaml`.
- gitleaks: `GITLEAKS_VERSION` ↔ `gitleaks/gitleaks` rev.

## Not done / user's call
- dependabot has no `cooldown` (semgrep MEDIUM finding).
- GitHub rulesets (immutable tags, trunk) server-side; `challenge/notes.md` TODO "main checks gh rules".
