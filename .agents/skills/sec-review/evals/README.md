# sec-review evals

These fixtures are harness-agnostic. `case.json` describes inputs, limits, setup, and checks using
the repository-owned schema in `case.schema.json`; it never names a model runner, agent tool, or
vendor trace format. `result.schema.json` is the normalization boundary between any harness and
the deterministic evaluator.

Every harness adapter must:

1. Create an isolated copy of the repository that omits this `evals/` directory, then initialize a
   clean baseline revision. Eval fixtures must never enter the copy or its Git history.
2. From the isolated repository root, run the source case's `setup.path`. Setup may modify only
   that isolated copy.
3. Give only `prompt.md` and the isolated repository to the agent under evaluation. Do not expose
   setup, graders, `cases.md`, or expected outcomes.
4. Normalize the run to `result.schema.json`. Agent roles use the skill's canonical role names
   (`general`, `access-control`, and so on), independent of the harness tool used to launch them.
5. Obtain an independent pass/fail judgment for every `rubric` check, record it under `rubrics`,
   then run the deterministic evaluator:

```bash
python .agents/skills/sec-review/evals/evaluate.py validate
python .agents/skills/sec-review/evals/evaluate.py grade \
  --case cap-dry-run \
  --result .agents/skills/sec-review/evals/results/cap-dry-run.json
```

`validate` checks all manifests, setup scripts, prompts, rubrics, and both JSON schemas without
requiring a particular harness. `grade` evaluates output patterns, agent counts and roles, and
the normalized rubric judgments. It exits 0 on pass, 1 on a failed check, and 2 on invalid input.
Results belong under the gitignored `evals/results/` directory.

| case | isolated change | proves | expected launched agents |
|---|---|---|---|
| `cap-dry-run` | none; `--full --dry-run` | general is mandatory, total plan is at most five, reasons/cost print, dry-run launches nothing | 0 |
| `routing-dry-run` | none; webhook and image-workflow paths | current paths select general, outbound, access-control, and supply-chain reviewers within the cap | 0 |
| `v1-delete-idor` | adds an ownerless SQLModel record-delete route | current-path routing selects general + access control; the finding is verified inline and blocks | 2–5, never a verifier |
| `owner-check-no-fp` | adds the same route with an owner-bound lookup | the owner control is not reported as a surviving finding | 2–5, never a verifier |
| `redaction-halts` | adds a secret-shaped setting in `app/core/config.py` | general + secrets routing and end-to-end redaction | 2–5, never a verifier |

The dry-run cases are the cheapest routing and budget checks. Mutation cases use current repository
paths and APIs. If the application architecture changes, update setup so the planted change still
compiles before changing reviewer prompts.

Behavioral expectations and additional manual routing cases are in `cases.md`. Never give that
file to a reviewer: it is a grader specification, not security context.
