# Reviewer ground rules (read before your reviewer file)

You are one reviewer in a fan-out security review. You see a redacted context pack and one
reviewer file that says what you look for. Other reviewers cover everything else; do not drift.

## What is in the pack

| file | use it for |
|---|---|
| `MANIFEST.md` | mode (diff / full), redaction status, which in-scope paths were withheld |
| `diff.patch` | the change under review (diff mode). Empty in full mode |
| `changed-files.unredacted.txt` | the only files you may open. In full mode this is the whole in-scope tree |
| `route-map.md` | every HTTP route with params, dependencies and flags; the worklist for request-driven reviewers |
| `auth-model.md` | who may do what, per resource. Ground truth; code that disagrees with it is a finding |
| `repo-conventions.md` | repo policy: exempt files, pin conventions, release topology. Hold the diff to these, not stricter ones |
| `findings.json` | normalized scanner results for the in-scope files. A hit you confirm is deterministic evidence |
| `signals.json` | why your reviewer was selected; ignore otherwise |
| `codeowners.txt` | fill `suggested_owner` |

Do **not** open `baseline.md`; it is for the verifier. Reading it would anchor you on
what is already known instead of what is new.

## Standalone invocation

You may be run on your own (`@agent-sec-review-<name>`) rather than by the sec-review
orchestrator. Then: the pack is `.sec-review/` at the repo root. If `.sec-review/MANIFEST.md`
does not exist, stop and reply with exactly one line telling the caller to run
`uv run python .agents/skills/sec-review/scripts/context_pack.py` first; do not build it
yourself. No other reviewers are running, so cover your whole file; do not defer to
reviewers that are not present. Write your array to `.sec-review/raw/<name>.json` only if
the caller asks; otherwise return it.

## Rules

1. **Read-only.** Do not execute code, run tests, start servers or send requests. Trace and
   cite; give the verifier a concrete thing to try.
2. **Stay inside the pack.** Open only files listed in `changed-files.unredacted.txt`, plus a
   file a changed file directly imports when you need it to see a sink or a control. Say
   when you needed one. If a path is redacted, do not guess its contents; the
   `secrets-crypto` reviewer handles "secret-bearing file changed".
3. **Diff mode reviews the change.** A pre-existing defect in an unchanged line is out of
   scope unless the change makes it reachable or worse. Full mode reviews the tree.
4. **One finding per defect.** If two lines are the same defect, one finding, both lines in
   `evidence.sources`.
5. **No fixes.** `fix_direction` names the missing control in one sentence, no code.
6. **Empty is a valid answer.** Return `[]` rather than padding with speculation.

## Confidence

- `high`: you quote the source, the sink and the absence of the control, all in files you
  opened.
- `medium`: the pattern matches but a control could exist in code you could not see, or the
  reachability depends on an assumption. Name the assumption.
- `low`: a suspicion worth a verifier's time. Say what would confirm it.

## Evidence

- `findings.json` hit for the same file/line/class that you confirmed → `kind: scanner`,
  `ref: <tool>/<rule id>`, `deterministic: true`.
- Otherwise `kind: reasoning`, `ref: <source line> -> <sink line> -> <return line>`,
  `deterministic: false`, and describe the exact request or command the verifier should
  run.

## Output

Return only a JSON array of `finding` objects matching `schema.json`. `class` is your reviewer
name; `id` is `<reviewer>-<n>`. `why_here` states the impact in this service using
`auth-model.md` and `route-map.md`, not a CWE description.
