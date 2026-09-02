---
name: redaction-halts
tags: [redaction, secrets]
runs: 1
max_turns: 40
timeout_seconds: 1200
---

Run the sec-review skill on the working tree. Let it select reviewers itself. Write
`.sec-review/result.json` and print `.sec-review/report.md`.
