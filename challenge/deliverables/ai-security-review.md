# AI-Assisted PR Security Reviewer

Design for a PR reviewer on this repo. A lite local version exists as the `sec-review` agent skill (`.agents/skills/sec-review/`): twelve portable reviewer prompts, an adversarial verifier, a capped orchestrator, `claude plugin eval` cases. It runs inside the developer's coding-agent session, not CI.

## Inputs

- **Diff**: `git diff <base>` plus changed-file list. The change is the unit of review; unchanged defects count only if the change makes them reachable.
- **Route map**: method, path, handler, params, dependencies, response model for every route. Worklist for access-control, injection and exposure reviewers. (Local: each reviewer reads the routers; CI should generate it once from the app.)
- **Auth model notes**: `context/auth-model.md`, hand-maintained. Identity, the three authorization styles in the code, which resources are tenant-scoped, who may read/write each, and patterns that are deliberately not findings. Code that disagrees is a finding; an undeclared resource is a medium finding whose fix is the declaration.
- **Scanner findings**: `.sarif/` from semgrep, bandit, gitleaks, osv-scanner. The deterministic tier.
- Also: `context/repo-conventions.md` (exempt files, pins, release topology, test accounts), `context/baseline.md` (triaged findings, **verifier only** so reviewers measure discovery not memory), CODEOWNERS.

## Outputs

One report, printed (CI: one PR comment plus check conclusion). Schema in `schema.json`.

- **Risk label**: highest surviving severity, `critical…none`.
- **Findings**: class, CWE, `file:line`, summary, `why_here` (impact in this service via the auth model, not a CWE description). Secret values never quoted.
- **Confidence**: `high` = source, sink and missing control quoted; `medium` = a control may exist out of view, assumption named; `low` = suspicion with a stated confirm step. Verifier raises on reproduction, lowers on assumption.
- **Suggested owner**: CODEOWNERS, else last committer of the line.
- **Decision**, first match wins: `escalate` for a surviving, unbaselined auth bypass, live credential or cross-tenant write; `block` only when severity ≥ high **and** confidence high **and** deterministic evidence **and** not baselined; `comment` for confidence ≥ medium or baselined would-be blocks; `pass` otherwise.
- Mandatory sections **Baselined** (downgraded, with id) and **Not flagged** (every killed finding with kill reason): the false-positive record.

## Guardrails

- **No AI-only blocking.** Reasoning alone is `comment` at most; low confidence never blocks.
- **Deterministic evidence for failure**, in order: scanner hit at the same file/line/class; a repo test that fails now (`tests/test_authz_invariant.py` failed on both access-control findings); a reproduction the verifier executed with the test client from a throwaway script; a command whose output demonstrates a config fact. Reviewers are read-only; only the verifier runs code and it records what it ran.
- **False-positive detection.** A fresh-context verifier per reviewer tries to kill each finding: wrong line, control exists (traced through helpers), unreachable, exempt fixture, intended shared resource, already baselined. Reviewers never see each other's output.
- **Secrets.** Local version runs in the developer's own session, so nothing leaves the boundary it is already in; findings still never echo values, and an eval plants a marker in `config/dev.py` that must not appear in the report. The only real control point for keeping secrets out of other models is network egress, not in-flight prompt scrubbing, and even egress-level scanning is effectively infeasible: prompt requests can be massive and large-scale WAFs typically only buffer around 128KB.
- **Cost cap.** At most five reviewers chosen from what the diff touches, at most one verifier per reviewer with findings, plan and estimate printed first; only an explicit reviewer list lifts the cap. Learned the hard way: the first design used ~1.9M tokens in one run.
- Diff and comment content is data, not instructions. No fixes. Repo policy lives only in `context/`; reviewer prompts stay portable, so they cannot become a regression tester for known defects.
- **Sandboxing.** If this were to be moved into a CI environment, sandboxing would be essential; I have built a sandboxing environment for AI agents, covered in `CONTRIBUTING.md`.

## Evaluation

- **Agent Skills Evals**: I would largely lean on the canonical [https://agentskills.io/skill-creation/evaluating-skills](https://agentskills.io/skill-creation/evaluating-skills) framework for structured evaluation
- **Seeded cases**: `evals/cases.md` lists the eleven seeded defects with owning class and eight expected non-detections (`/me`, `/notes`, staff gate, fixtures, `test.yml`, pinned actions, advisory-scan topology). Never reviewer input. Run on `app/routes/` 2026-09-02: all in-scope seeds found and verified, no non-detection survived.
- **False-positive rate**: from "Not flagged" by kill kind, plus owner disposition. Same run: 14 raised, 4 killed (all duplicates), 10 survived, 0 blocks (9 baselined, 1 new medium: no login throttling). Also `block` precision; target is no overturned block.
- **Missed BAC variants**: nine unseeded variants (delete route, id in query, helper lookup, role from body, inverted boolean, undeclared resource, mass assignment, batch lookup, unchecked sibling export). Four automated with scaffold + graders on the printed report; inverted boolean is an accepted static miss the verifier's reproduction should catch. Misses are logged in `cases.md`, never patched into a prompt.
- **Engineering feedback**: accepted / rejected / already-known per finding; rejected feeds FP rate, already-known outside the baseline means the baseline is stale.
- Also tracked: subagents and tokens vs estimate (routes run: 5 + 5, ~330k, inside estimate), reviewers selected and why, cap hits, kill counts by kind, comment-to-fix time. I have built comprehensive tracking and reporting mechanisms in my sandboxing solution to capture metrics for continuous improvement, egress, tool calls, mcp connections, plugin use, and costs.
