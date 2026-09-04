# sec-review refresh status

Updated 2026-09-04.

- Default scope precedence is explicit in `.agents/skills/sec-review/SKILL.md`: user scope wins; otherwise an open PR for the current branch is reviewed; without one, the branch plus tracked working-tree changes and untracked non-ignored files are reviewed.
- Every non-empty orchestrated run includes `sec-review-general`. The general reviewer performs a holistic attacker-minded pass.
- The entire orchestration has a hard five-subagent ceiling with no override. At most four specialists run beside general, there is no second reviewer wave, and verification runs inline rather than launching verifier agents.
- `context/reviewer-routing.md` maps current FastAPI, SQLModel/Postgres, test, script, workflow, container, dependency, and agent paths to specialist candidates, with content-based confirmation and impact ranking.
- Auth, repository conventions, baseline, verifier guidance, and SQLModel eval scaffolds match the current codebase. `schema.json` enforces 1–5 selected reviewers, exactly one general reviewer, and zero launched verifiers with inline verification.
- `scripts/sync_agents.py` reads root AGENTS guidance into every generated agent. All 13 `.codex/agents/sec-review-*.toml` files are synchronized.

## Portable eval contract

- The old vendor-specific plugin-eval manifests were removed.
- Each case now uses repository-owned `case.json`, a separate `setup.sh`, a plain prompt, and semantic rubrics.
- `evals/case.schema.json` and `evals/result.schema.json` define a harness-neutral normalization boundary. Canonical agent roles are independent of launch-tool names.
- `evals/evaluate.py` validates cases and grades normalized outputs, agent counts/roles, rubric judgments, and run status. Exit codes are 0 pass, 1 failed case, and 2 invalid input.
- Eval fixtures must be omitted from the isolated repository and its Git history before the subject runs.
- Local results are ignored through `.gitignore`.

## 2026-09-04 eval results

One normalized run per case using isolated repository copies and independent semantic judges:

- PASS `cap-dry-run`.
- FAIL `routing-dry-run`: the generalist reason was generic rather than tied to the requested paths.
- PASS `v1-delete-idor`: three reviewers; deterministic mounted cross-owner deletion; critical/escalate.
- FAIL `owner-check-no-fp`: no finding survived and the owner control worked, but killed route findings were labeled `other` instead of `control-exists`.
- PASS `redaction-halts`: two reviewers; high/block; secret value remained redacted.

Aggregate: 3 passed, 2 failed. Results and misses are recorded in `evals/cases.md`.

The nested CLI adapter could not exercise child-agent fan-out in this container (ephemeral sessions could not register a child thread; normal sessions produced empty waits), so mutation cases used the current session's native named-agent interface. This adapter limitation is separate from the portable case/result contract.

## Verification

Passed: portable manifest validation; evaluator positive, negative, duplicate-role, and timeout behavior; shell setup syntax; Ruff check/format; skill quick validation; generated-agent drift check; forbidden-scope and vendor-specific eval syntax searches; `git diff --check`.
