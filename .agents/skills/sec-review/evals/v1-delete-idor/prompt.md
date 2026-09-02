---
name: v1-delete-idor
tags: [access-control, variant, block]
runs: 1
max_turns: 40
timeout_seconds: 1200
---

Run the sec-review skill on the working tree (diff against HEAD) with only the
`access-control` reviewer, then the verifier, then the decision, and print the report.
