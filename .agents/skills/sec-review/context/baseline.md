# Baseline — sec-review findings

This project-owned file is read only by the inline verifier. Reviewers must not open it.

There are currently no active human-triaged sec-review findings. Do not recreate or suppress
historical findings that no longer match the current SQLModel/PostgreSQL application.

When a finding is deliberately accepted, add a row with a stable id, class, repository-relative
location, status, reason, and review/expiry date. A matching entry means the finding remains real
but is reported as `comment`; it cannot produce `block` unless the reviewed change makes the risk
worse than the accepted entry.

| id | class | where | status | reason | review or expiry |
|---|---|---|---|---|---|

## Other baseline sources

- `gitleaks-report.json` is redacted. A match survives as baselined only when the scan also used
  `--redact`; never copy a matched value into a report.
- `osv-scanner.toml` entries suppress a dependency finding only while `ignoreUntil` is in the future
  and the entry has a concrete reason.
