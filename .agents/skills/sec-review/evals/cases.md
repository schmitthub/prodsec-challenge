# sec-review evaluation cases

Evaluation artifacts are harness-only and never reviewer input. All security regressions are
planted in scratch copies; the current application is the control, not a collection of permanent
expected findings.

## Scope, routing, and budget expectations

| id | request/scope | expected behavior |
|---|---|---|
| R1 | no explicit scope, current branch has an open PR | review exactly the PR base/head diff |
| R2 | no explicit scope and no open PR | review branch plus tracked working-tree diff and untracked non-ignored files |
| R3 | explicit `app/api/routes/webhooks.py` | `general` plus `outbound-requests` and `access-control`; content may qualify `data-exposure` or `input-validation-dos` |
| R4 | explicit `.github/workflows/` | `general` plus `supply-chain-ci`; add `secrets-crypto` or `injection` only for matching content |
| R5 | any non-empty automatic run | `general` is present and no more than five reviewer agents launch |
| R6 | up to four named specialists | run those specialists plus `general`, with no auto-added specialist |
| R7 | more than four named specialists | print the over-cap plan and launch no agent |
| R8 | empty default diff | print `nothing to review` and launch no agent |

`--dry-run` must print the resolved scope, reasons for every selected and omitted specialist, and
estimated cost while launching zero agents. The five-agent limit counts the entire orchestrated
run; verification is inline and never creates a verifier agent.

## Scratch-copy detection variants

| id | planted regression | expected owner | expected result when deterministically reproduced |
|---|---|---|---|
| V1 | record delete by id without owner check | `access-control` | high/critical block or escalate |
| V2 | search drops `Record.user_id == current_user.id` | `access-control` | high block |
| V3 | search interpolates `q` into raw SQL text | `injection` | high/critical block |
| V4 | webhook drops exact-host allowlist, HTTPS check, redirect guard, or timeout | `outbound-requests` | high block when internal/unapproved egress is reproduced |
| V5 | token decode disables expiry or accepts an attacker-selected algorithm | `authentication` | high block |
| V6 | runtime configuration gains a literal production credential | `secrets-crypto` | high block; value always redacted |
| V7 | a workflow action becomes mutable or release subject is rebuilt after signing input selection | `supply-chain-ci` | high block when structural evidence proves it |
| V8 | generic exception detail becomes reachable outside local mode | `data-exposure` | medium/high comment or block by evidence |
| V9 | request data supplies role/owner fields used for authorization or persistence | `access-control` | high/critical block |
| V10 | archive/upload/XML/YAML parsing is added without safe-mode or resource controls | `unsafe-parsing-files` | severity follows reachable impact |

A prompt change is justified only when it improves the whole vulnerability class, not because it
names one variant above.

## Current-control false-positive probes

| id | current behavior | why it must not survive | expected kill/absence |
|---|---|---|---|
| N1 | `GET /me` returns token-derived current user | no client-selected identity | reviewer absence or `intended-shared-resource` |
| N2 | record read compares `Record.user_id` to `current_user.id` | owner control exists | `control-exists` |
| N3 | foreign and missing records both return 404 | required anti-enumeration behavior | reviewer absence |
| N4 | record-note read permits owner or staff | declared staff-wide exception | `intended-shared-resource` |
| N5 | search uses owner filter plus SQLModel auto-escaped substring matching | tenant and injection controls exist | `control-exists` |
| N6 | webhook uses HTTPS exact-host allowlist, no redirects, timeout, and bounded preview | outbound controls exist | `control-exists` |
| N7 | local fixture password comes from settings and seeding is local-only | not a literal production credential | `test-or-fixture-code` or reviewer absence |
| N8 | generic error detail includes `repr` only in local mode | production path is generic | `unreachable` or reviewer absence |
| N9 | API documentation and health are public | explicitly intended endpoints | `intended-shared-resource` |
| N10 | `requirements.txt` and `Dockerfile.old` exist but active workflows use uv inputs | inactive legacy artifacts | `test-or-fixture-code` or reviewer absence |
| N11 | image signing depends on `build`, not advisory `scan` | documented release topology | reviewer absence |
| N12 | Docker build runs as root then sets `USER app` for runtime | privilege is dropped | `control-exists` |

## Automated cases

`evals/README.md` documents the harness-neutral case and result contract. Current automated
coverage includes:

- `cap-dry-run`: full-project planning, mandatory generalist, hard cap, and zero dry-run agents.
- `routing-dry-run`: webhook plus image-workflow path routing with zero launched agents.
- `v1-delete-idor`: V1 against the current SQLModel route layout.
- `owner-check-no-fp`: N2-shaped delete with the correct owner check.
- `redaction-halts`: V6 in the current configuration module without revealing the marker.

## Metrics

Record:

- detection variants hit/missed and current-control probes that survived;
- reviewers selected, path/content reason, qualified reviewers omitted by the cap;
- normalized agent roles and total subagents launched, which must be 0–5, plus confirmation that
  verification stayed inline;
- deterministic block precision and verifier kill kinds;
- approximate tokens, wall time, and code-owner disposition.

## Run log

| date | revision | scope/case | reviewers | hit or control result | false positives | subagents | notes |
|---|---|---|---|---|---|---|---|
| 2026-09-04 | `9c1bc25+wt` | `cap-dry-run` | general + 4 planned specialists | pass | 0 | 0 | cap, reasons, cost, and dry-run stop passed |
| 2026-09-04 | `9c1bc25+wt` | `routing-dry-run` | general, outbound-requests, access-control, supply-chain-ci, secrets-crypto | miss | 0 | 0 | generalist reason was generic instead of path-specific |
| 2026-09-04 | `9c1bc25+wt` | `v1-delete-idor` | general, access-control, business-logic | hit; critical escalate | 0 | 3 | direct invocation proved mounted cross-owner deletion |
| 2026-09-04 | `9c1bc25+wt` | `owner-check-no-fp` | general, access-control, business-logic | control held; rubric miss | 2 killed | 3 | no finding survived, but kill kind was `other` instead of `control-exists` |
| 2026-09-04 | `9c1bc25+wt` | `redaction-halts` | general, secrets-crypto | hit; high block | 0 | 2 | duplicate merged; normalized output remained redacted |

## Known misses

Record a miss with its variant class, observed output, and root cause. Keep a prompt change only if
it generalizes to sibling defects outside the recorded case.

- 2026-09-04 `routing-dry-run`: required specialists were selected within the cap, but the
  generalist reason said only “mandatory cross-class review.” The plan formatter needs to tie the
  mandatory role to the requested webhook and image-workflow boundaries.
- 2026-09-04 `owner-check-no-fp`: inline verification correctly left no surviving finding after
  the owner check rejected a foreign UUID, but it classified two killed policy claims as `other`.
  The verifier should use `control-exists` when an owner comparison deterministically defeats the
  claimed authorization gap.
