# sec-review skill fixes handoff

Scope: modify only `.agents/skills/sec-review/`. Keep the handoff focused on actionable skill fixes.

## Non-negotiable boundary

The skill must contain zero references to `challenge/`. That directory is scenario material, not a project policy, baseline, evaluation, or documentation source. Remove dependencies; do not repoint them to a different path under that directory.

Current references to remove:
- `SKILL.md:8` — remove the claim that the skill is a reference implementation of a file under `challenge/`.
- `context/auth-model.md:15` — remove the external triage reference. Keep the identity weaknesses self-contained or point to project-owned skill context.
- `context/repo-conventions.md:8-10` — replace scenario triage/reachability paths with project-owned baseline metadata outside `challenge/`.
- `eval/cases.md:5` — remove the scenario triage destination for misses.

Baselining must remain auditable:
- Decide on a project-owned baseline source outside `challenge/`.
- Make that source available inside the generated context pack; correcting a path without packaging the referenced content does not satisfy the reviewers' pack-only boundary.
- For eval misses, `.sec-review/report.md` already records hit/miss/false-positive results. If results must persist across runs, add a tracked file under `.agents/skills/sec-review/eval/`.

## Portable context-pack status

File: `scripts/context-pack.sh`.

Current SARIF status construction uses GNU-only `stat -c %y`. On BSD/macOS, this fails when SARIF files exist; with `set -euo pipefail`, the final failing command substitution can terminate the script.

Do not treat a `stat` fallback alone as complete macOS support: the script also uses `mapfile`, which is absent from macOS's default Bash 3.2.

Required decision:
- If Linux is the supported execution platform, document that explicitly and keep the implementation Linux-specific.
- If macOS/manual-host execution is supported, replace both GNU/Bash-version-specific constructs and verify the whole script with the supported shell, not only the mtime decoration.
- If SARIF mtime has no behavioral value, dropping it is the narrowest fix for the immediate `stat` dependency, but it does not resolve `mapfile`.

## Release artifact invariants

The image scan is intentionally advisory and release signing intentionally depends on `build`, not `scan`. Both downstream jobs consume the same archive emitted by `build`. Update all skill guidance to encode artifact identity rather than a mandatory build → scan → sign job chain.

Files:
- `context/repo-conventions.md:34`
  - Replace “Release chain: build → scan → sign.”
  - Describe the actual topology: build → best-effort scan and build → release-only sign.
  - State that both must consume the exact build-produced archive/digest.
- `reviewers/supply-chain-ci.md:34-35`
  - Remove “sign job that doesn't need scan” as a provenance failure.
  - Flag scan/sign/attestation steps that rebuild, pull, substitute, or otherwise target a different artifact than the build output.
  - Require sign-after-scan only when repository policy explicitly makes scanning a release gate.
- `reviewers/supply-chain-ci.md:63`
  - Replace “sign job not depending on scan | high”.
  - High severity should apply to a verified signature/attestation subject mismatch, not the absence of a `needs: scan` edge.

Keep these three edits semantically identical so the repo convention, reviewer checklist, and severity table cannot contradict each other.

## Verification gates

- `rg -n 'challenge/' .agents/skills/sec-review` returns no matches.
- Shell syntax/static checks pass for `scripts/context-pack.sh`.
- Build a context pack with SARIF absent and present; both paths complete successfully on every documented supported platform.
- Confirm the generated pack includes whatever project-owned baseline source the reviewers must consult.
- Review the three release-artifact statements together and confirm none requires advisory scan completion before signing.
