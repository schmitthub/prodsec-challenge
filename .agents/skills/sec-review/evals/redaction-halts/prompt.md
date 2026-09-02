---
name: redaction-halts
tags: [redaction, secrets]
runs: 1
max_turns: 40
timeout_seconds: 1200
---

Run the sec-review skill on the working tree (diff against HEAD). Let it select reviewers
itself, then print the report.
