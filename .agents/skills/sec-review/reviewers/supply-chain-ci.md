# Reviewer: supply-chain-ci

Class: the pipeline and the artifact. GitHub Actions security (CWE-94 via expression
injection, CWE-250 over-broad permissions, CWE-829 unpinned actions), dependency and
lockfile hygiene (CWE-1104, CWE-1395), container hardening (CWE-250 root, CWE-1188),
release integrity (signing, attestation, immutable tags).

## Read, in order

1. `MANIFEST.md`.
2. `findings.json` — semgrep `p/github-actions` hits (SARIF `semgrep-actions`), osv-scanner
   results. Confirm; these are deterministic.
3. `changed-files.txt` filtered to `.github/`, `Dockerfile`, `.dockerignore`,
   `pyproject.toml`, `uv.lock`, `requirements.txt`, `.pre-commit-config.yaml`,
   `.gitleaks.toml`, `osv-scanner.toml`, `.semgrepignore`, `.gitleaksignore`, `scripts/`.
4. `diff.patch` for those files. On `--full`, read them whole.

Read `repo-conventions.md` in the pack for the conventions this repo holds itself to
(pin style, baseline handling, policy-exempt files). Hold the diff to those; do not
invent stricter ones.

## Look for

**Workflows**
- `${{ github.event.* }}` / `${{ inputs.* }}` / `${{ steps.*.outputs.* }}` interpolated
  directly into `run:` — expression injection. Should go through `env:`.
- `pull_request_target` with checkout of the PR head; `workflow_run` trusting artifacts.
- `permissions:` missing, or `write-all`, or a job that has `contents: write` /
  `id-token: write` without needing it. Reusable workflows: permissions declared per
  *calling* job — check the callers, not the callee.
- Actions pinned by tag or branch instead of SHA; SHA with a stale/wrong version comment.
- Secrets passed to third-party actions or echoed; `ACTIONS_STEP_DEBUG`.
- Cache poisoning: cache key derived from PR-controlled input, restored on main.
- Artifact provenance: build → scan → sign chain broken (sign job that doesn't `need` scan,
  scan that pulls instead of consuming the built artifact).
- Severity gates loosened: a scanner's fail threshold raised, `continue-on-error: true`
  added, a baseline regenerated in the same PR that adds the finding it baselines.

**Dependencies**
- `requirements.txt` and `uv.lock` disagreeing on a pin (two dep surfaces in this repo).
- New dependency with no lockfile change; version range instead of a pin; git/URL deps.
- `osv-scanner.toml` ignores added without a reason and an expiry.
- Dockerfile `pip install` from `requirements.txt` while the lock says otherwise.

**Container**
- Runs as root (no `USER`); `latest`/unpinned base image; secrets in build args or layers;
  `--reload` in `CMD`; `.dockerignore` missing `.git`, `.env`, `tests`.

**Suppression hygiene**
- Any new `# nosemgrep`, `# nosec`, `.gitleaksignore` line, `.semgrepignore` path, or
  `paths-ignore` in CodeQL config without an adjacent justification. Flag every one; the
  verifier decides if it's legitimate. Suppressions are the primary way a pipeline rots.

## Severity

| situation | severity |
|---|---|
| expression injection in `run:` on a workflow with write perms or secrets | critical |
| `pull_request_target` + PR head checkout | critical |
| unpinned third-party action | high |
| over-broad `permissions` on a job handling secrets/OIDC | high |
| gate loosened / scanner disabled / unjustified suppression | high |
| sign job not depending on scan | high |
| lock/requirements drift, root container, `latest` base | medium |
| stale version comment on a correct SHA | low |

## Evidence

semgrep-actions or osv hit → deterministic. Structural facts you can verify with a command
count too — run it and record it: `grep -n 'uses:' .github/workflows/*.yml | grep -v '@[0-9a-f]\{40\}'`
→ `kind: reproduction`. Everything else is reasoning.

## Not findings

- Files `repo-conventions.md` lists as policy-exempt, for being what they are.
- SHA-pinned actions whose comment version you can't verify offline — note as `info`, don't
  flag.
- Suppressions **with** a justification comment that references a triage entry.

## Output

JSON array of `finding`, `class: "supply-chain-ci"`, ids `supply-chain-ci-<n>`.
