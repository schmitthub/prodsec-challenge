# Lens: supply-chain-ci

The pipeline and the artifact. CI expression injection (CWE-94), over-broad permissions
(CWE-250), unpinned or mutable dependencies and actions (CWE-829, CWE-1104), dependency
and lockfile hygiene (CWE-1395), container hardening (CWE-250, CWE-1188), artifact
integrity and provenance (CWE-345, CWE-494), scanner and gate suppression.

Read `_common.md` first, then `repo-conventions.md`: it states the pin style, baseline
handling, policy-exempt files and the release topology this repo commits to. Hold the
diff to those; do not invent stricter ones.

## Worklist

1. `findings.json`: CI and dependency scanner hits. Confirm; deterministic.
2. Changed workflow files, composite actions, container files and ignore files, lockfiles
   and manifests, pre-commit config, scanner configs and baselines.

## Look for

**Workflows**
- Event or input expressions interpolated into `run:` instead of passed through `env:`.
- Privileged triggers (`pull_request_target`, `workflow_run`, `issue_comment`) that check
  out or execute untrusted code, or trust untrusted artifacts.
- Missing or broad `permissions:`; write, id-token or attestation scopes on jobs that do
  not need them. Reusable workflows take permissions from the caller: check callers.
- Actions or images pinned by tag or branch; a digest whose version comment disagrees.
- Secrets passed to third-party steps, printed, or reachable from fork PRs.
- Cache keys derived from untrusted input, restored on trusted branches.
- Self-hosted runners for untrusted triggers.

**Artifact identity**
- Any scan, sign or attest step that rebuilds, pulls, or otherwise targets something
  other than the exact build output (digest or archive) it claims to cover. That is the
  provenance break. Job ordering alone is not: a sign step is allowed to depend only on
  build when `repo-conventions.md` says scanning is advisory.
- Sign-after-scan required only where repository policy makes the scan a release gate.
- Attestation subject or signing identity that does not match the artifact or the
  workflow that built it.

**Gates and suppressions**
- Fail thresholds raised, `continue-on-error` added, a scanner removed or narrowed,
  a baseline regenerated in the same change that introduces what it baselines.
- New inline suppressions (`nosec`, `nosemgrep`, ignore-file entries, config
  `paths-ignore`) with no adjacent justification pointing at a tracked decision.

**Dependencies**
- Manifest and lockfile disagreeing; new dependency without a lockfile change; version
  ranges instead of pins; git or URL dependencies; install steps reading a different
  manifest than the lockfile that the SBOM and scanners read.
- Vulnerability-ignore entries without a reason and an expiry.

**Container**
- Runs as root; mutable base tag; secrets in build args or layers; dev-mode entrypoint;
  ignore file that lets secrets, VCS metadata or tooling into the image.

## Severity

| situation | severity |
|---|---|
| expression injection on a workflow with write permissions or secrets | critical |
| privileged trigger executing untrusted code | critical |
| verified signature or attestation subject mismatch with the built artifact | high |
| unpinned third-party action or image | high |
| over-broad permissions on a job holding secrets or OIDC | high |
| gate loosened, scanner disabled, unjustified suppression | high |
| manifest/lockfile drift, root container, mutable base tag | medium |
| stale version comment on a correct digest | low |

## Evidence

Structural facts count as reproduction when you can state the command whose output
demonstrates them; the verifier runs it. Example shape: a grep for `uses:` lines lacking a
40-hex digest.

## Not findings

- Files `repo-conventions.md` lists as policy-exempt, for being what they are.
- Digest-pinned actions whose version comment you cannot verify offline: `info`.
- Suppressions with a justification that references a tracked decision.
