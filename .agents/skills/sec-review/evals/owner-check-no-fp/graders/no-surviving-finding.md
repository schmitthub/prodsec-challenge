---
type: regex
target:
  source: file
  path: .sec-review/result.json
match: contains
---

"decision":\s*"pass"
