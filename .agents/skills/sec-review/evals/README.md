# sec-review evals

Runner: `claude plugin eval` (Claude Code, early access). Each case dir holds `prompt.md`
(frontmatter + the user turn), `case.yaml` (`scaffold_script` that plants a variant in a
scratch copy of the repo before the turn runs), and `graders/*.md`. `cases.md` is the
harness-agnostic spec these cases implement; keep the two in step.

```bash
# from the repo root; one run per case, hard cost ceiling, local report only
claude plugin eval .agents/skills/sec-review \
  --runs 1 --allow-tools Bash Write Agent \
  --max-cost-usd 20 --no-publish --json .agents/skills/sec-review/evals/results/last.json

claude plugin eval .agents/skills/sec-review --case 'cap-*'      # one case
claude plugin eval .agents/skills/sec-review --keep-temp --verbose   # debug a scaffold
```

Exit 0 = every case at or above `--threshold` (default 1.0); 1 = a case failed; 2 = cost
ceiling hit. Results land in `evals/results/<timestamp>/`.

| case | plants | proves | subagents |
|---|---|---|---|
| `cap-dry-run` | nothing; `--full --dry-run` | plan printed, ≤5 reviewers chosen, cost stated, **no** subagent spawned | 0 |
| `v1-delete-idor` | `DELETE /api/records/{id}` with no owner check (cases.md V1) | an unseeded BAC variant is found by `access-control`, verified, and blocks | ≤2 |
| `owner-check-no-fp` | same route **with** the owner check | no finding survives (cases.md N2 shape) | ≤2 |
| `redaction-halts` | a new key in `../../../../config/dev.py` | report names the file; the planted value is never echoed in the report | ≤2 |

Cost: the three fan-out cases spawn at most one reviewer and one verifier each, roughly
100–150k tokens per case. The dry-run case is a few thousand. The seeded S-table in
`cases.md` is not encoded here on purpose: it is the baseline, not the generalisation
test; add a case only for a variant the reviewers have never been told about.

Grader format follows Claude Code 2.1.258 `plugin eval --help`; if the first run reports a
grader parse error, fix the format here before touching the skill.
