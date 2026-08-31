# CI / release pipeline

## Layout (`.github/workflows/`)
- `pr.yml` (PR→main) and `main.yml` (push main) → call `security.yml` (semgrep SARIF→code scanning, gitleaks CLI w/ `--baseline-path gitleaks-report.json`, dependency-review on PR only) and `test.yml`.
- `release.yml` (tag `v*`): `validate` (semver regex; tag must be ancestor of `origin/main`) → `build.yml` (`workflow_call`). Build job perms: `contents: write`, `id-token: write`, `attestations: write`, `artifact-metadata: write` (actions/attest@v4).
- Verify: `gh attestation verify <artifact> --owner schmitthub --signer-workflow schmitthub/prodsec-challenge/.github/workflows/build.yml`.
- `.semgrep/actions.yaml`: `pull_request_target` + cache-capable action rule. App BAC/IDOR rule still TODO here.
- GitHub rulesets (immutable tags, trunk-based) are server-side, not in repo.

## Known-wrong scaffolding (copied from clawker Go repo) — fix, don't preserve
- `security.yml`: `--config p/golang` → should be `p/python`/`p/owasp-top-ten`; duplicate `test` job (already in `test.yml`); dependabot comment mentions go.mod.
- `build.yml`: installs cosign+syft, no build/SBOM/sign steps; attests `release-subjects/*` which nothing creates. Target: build → syft SBOM → cosign keyless → attest provenance + SBOM.
- `release.yml` goreleaser comments; `.syft.yaml` (go-module cataloger, `source.name: clawker`); `.gitleaksignore` Go paths; `.semgrepignore` Go comments; `.claude/settings.local.json` refs missing `go-commands.sh`; `.claude/docs/*` are clawker docs.
- `gitleaks-report.json` baseline missing → gitleaks hook/CI fail until created.
