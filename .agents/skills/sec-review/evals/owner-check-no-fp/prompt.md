---
name: owner-check-no-fp
tags: [access-control, false-positive]
runs: 1
max_turns: 40
timeout_seconds: 1200
---

Run the sec-review skill on the working tree with only the `access-control` reviewer,
then the verifier, then the decision and report. Write `.sec-review/result.json` and print
`.sec-review/report.md`.
