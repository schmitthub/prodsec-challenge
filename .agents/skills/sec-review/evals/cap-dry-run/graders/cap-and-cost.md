---
type: llm
focus: last_message
---

Pass only if all hold:
1. The plan names the reviewers that will run, and there are at most five of them.
2. Each named reviewer has a one-phrase reason tied to what the tree contains.
3. The plan states an approximate token cost or subagent count before any review happens.
4. The message says the run stopped at the plan (dry run) rather than reporting findings.
