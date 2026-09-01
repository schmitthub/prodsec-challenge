# CI / release pipeline

## Layout (`.github/workflows/`)
- `pr.yml` (PR→main), `main.yml` (push main) → call reusable `security.yml` + `test.yml`; permissions granted per calling job.
- `test.yml`: setup-uv (3.11, cache) → `uv sync --frozen` → ruff check + format --check → requirements.txt⊆uv.lock drift check (`uv export` vs pins) → unittest.
- `security.yml` (gating policy in header comment):
  - `semgrep` (container `semgrep/semgrep:<tag>@sha256`): single run, `--sarif-output` + `--json-output`; PR → `--baseline-commit $BASE_SHA`; inline python gate fails only on `ERROR|HIGH|CRITICAL`; main = upload only. `git config safe.directory` needed inside container.
  - `gitleaks`: checksum-verified binary (`GITLEAKS_VERSION`), `--config .gitleaks.toml --baseline-path gitleaks-report.json --redact`, SARIF.
  - `container`: `services.registry` (`registry@sha256…` = registry:3 on :5000) → `docker build` + `docker push localhost:5000/records-api:<sha>` → grype via `anchore/scan-action` with `image: registry:<digest-ref>` + `GRYPE_REGISTRY_INSECURE_USE_HTTP=true`, `fail-build` on `critical` + `only-fixed`. Commented block documents BuildKit `--sbom --provenance=mode=max --push` attestation flow (needs docker-container driver + real registry). Dockerfile = local dev only, not a release artifact.
  - `osv`: nested reusable `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml`, `fail-on-vuln: false`.
  - `dependency-review` (PR only, `fail-on-severity: high`).
- `release.yml` (tag `v*`): `validate` (semver, ancestor of origin/main) → `build.yml`. Build job perms: `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write`.
- `build.yml`: outputs go in `release-subjects/` (user's convention). No Docker. `git archive --prefix records-api-<tag>/` of the tag → `syft scan dir:.` (SPDX + CycloneDX; `.syft.yaml` excludes dist/tool state) → SHA256SUMS → `cosign sign-blob --bundle` each → `actions/attest@v4` twice: provenance mode (`subject-path: release-subjects/*`) and SBOM mode (`sbom-path`, subject = archive) — NOT the deprecated attest-build-provenance/attest-sbom wrappers → self-verify (`gh attestation verify --signer-workflow <repo>/.github/workflows/build.yml`, `cosign verify-blob --certificate-identity-regexp`) → `gh release create --verify-tag --generate-notes --notes-file`. Note: the uv wheel only packages `src/` stub, hence source archive not sdist/wheel.
- `.semgrep/actions.yaml`: `pull_request_target` + cache-capable action rule. App BAC/IDOR rule still TODO here.
- All actions SHA-pinned + `# vX.Y.Z`. Resolve SHAs from the container via `git ls-remote --tags git@github.com:<owner>/<repo>.git` (SSH open; HTTPS/API to non-allowlisted repos is 403). Use the peeled `^{}` SHA for annotated tags. Docker Hub digests: `docker pull` + `docker inspect --format '{{index .RepoDigests 0}}'` (daemon has host network).

## Pins that must move together
- semgrep: `security.yml` image tag ↔ `semgrep/pre-commit` rev in `.pre-commit-config.yaml`.
- gitleaks: `GITLEAKS_VERSION` ↔ `gitleaks/gitleaks` rev.

## Not done / user's call
- dependabot has no `cooldown` (semgrep MEDIUM finding).
- GitHub rulesets (immutable tags, trunk) server-side; `challenge/notes.md` TODO "main checks gh rules".
