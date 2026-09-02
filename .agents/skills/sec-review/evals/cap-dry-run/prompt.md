---
name: cap-dry-run
tags: [cost, selection]
runs: 1
max_turns: 15
timeout_seconds: 600
---

Run the sec-review skill in `--full --dry-run` mode on this repository. Print the plan it
produces and stop; do not run any reviewer.
