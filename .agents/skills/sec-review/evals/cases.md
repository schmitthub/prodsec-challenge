# Evaluation

Harness-only. Nothing here is reviewer input; the pack never contains this file. Reviewer
prompts must not be tuned toward these cases; a miss is recorded below, not patched away.

## How to run an eval

Automated cases live beside this file (`README.md` has the `claude plugin eval` command).
For a manual full-tree scoring run:

1. Run the skill with the reviewers under test named explicitly (see `SKILL.md`,
   "Arguments"). Naming reviewers is the only way past the five-reviewer cap, and it is a
   deliberate, costed choice.
2. Score the printed report against the tables below; append a row to "Run log".

## Seeded cases (expected detections)

These are the known defects in the tree (`context/baseline.md` mirrors them for the
verifier). Expected class is the reviewer that should own the finding.

| id | class | where | expected severity | deterministic evidence available |
|---|---|---|---|---|
| S1 | access-control | `app/routes/records.py` `read_record`: no owner check | high | test client repro (member reads another member's record → 200); `tests/test_authz_invariant.py` fails |
| S2 | access-control | `app/routes/search.py`: results not filtered to caller | high | repro; `tests/test_authz_invariant.py` |
| S3 | injection | `app/db.py` `search_records`: f-string SQL | critical | semgrep/bandit hit; repro |
| S4 | outbound-requests | `app/routes/webhooks.py`: GET to caller URL, no allowlist | high | semgrep/CodeQL; repro to a loopback URL |
| S5 | secrets-crypto | `app/auth.py` hardcoded `JWT_SECRET` | high | gitleaks/semgrep hit |
| S6 | authentication | `app/auth.py` `verify_exp: False` | high | semgrep if rule present; else reasoning |
| S7 | authentication | `app/db.py` plaintext passwords | high | bandit maybe; reasoning |
| S8 | data-exposure | `app/main.py` handler returns `repr(exc)` | medium | repro by forcing an exception |
| S9 | outbound-requests or data-exposure | `app/routes/webhooks.py` echoes upstream body | high | repro |
| S10 | supply-chain-ci | `Dockerfile` no `USER` | medium | structural grep |
| S11 | supply-chain-ci | `requirements.txt` vs `uv.lock` drift | medium | diff of pins |

## Expected non-detections (false-positive probes)

| id | where | why it must not survive | expected kill |
|---|---|---|---|
| N1 | `GET /api/me` | identity from token only | reviewer scope |
| N2 | `GET /api/records/{id}/notes` | owner check present | `control-exists` |
| N3 | webhook staff gate | role gate on a role-wide action (the SSRF is a separate real finding) | `intended-shared-resource` |
| N4 | `tests/test_records.py` credentials | fixture creds | `test-or-fixture-code` |
| N5 | redacted paths | only "file changed, review manually" allowed | redaction |
| N6 | `test.yml` | policy-exempt | reviewer scope |
| N7 | SHA-pinned actions | correct pattern | reviewer scope |
| N8 | `image.yml` sign depends on build, not scan | advisory scan by policy | `repo-conventions.md` |

## Broken-access-control variants (unseeded)

Apply each to a throwaway branch, run diff mode, record whether `access-control` (or any
reviewer) catches it. This is the generalisation check: a reviewer that only finds S1 is a
regression test, not a reviewer.

| id | variant | expected |
|---|---|---|
| V1 | `DELETE /api/records/{record_id}` with no check | access-control, critical |
| V2 | id via query param instead of path | access-control, high |
| V3 | lookup moved into a helper in another file | access-control, high; confidence may drop to medium |
| V4 | role read from the request body gates the return | access-control, critical |
| V5 | inverted boolean in an otherwise correct check | expected static miss; verifier repro should catch |
| V6 | new resource route not declared in `auth-model.md` | access-control, medium, "declaration missing" |
| V7 | `PATCH` writing `body.owner_id` into the record | access-control, critical (mass assignment) |
| V8 | batch route `POST /api/records:batchGet` taking a list of ids | access-control, critical |
| V9 | correct check on the route, sibling export route without it | access-control, high |

## Metrics to record per run

- hits / expected (S-table), misses by id
- false positives: anything surviving verify that a human rejects, plus any N-row that
  survived
- precision of `block`: blocks a human agreed with / all blocks
- verifier kill count by `false_positive_kind`
- reviewers selected and why; whether the cap was hit
- subagents spawned (reviewers + verifiers) and approximate tokens
- wall time
- engineering feedback: for each reported finding, disposition from the code owner
  (`accepted`, `rejected`, `already known`) and free text. Collected from the PR thread.

## Run log

| date | mode | reviewers | hits/expected | misses | FPs | blocks (agreed) | subagents | approx tokens | notes |
|---|---|---|---|---|---|---|---|---|---|
| 2026-09-02 | full | all (first design) | 11/11 | none | 0 listed | 4 (n/a) | 26 | ~1.9M | pre-redesign; per-finding verifiers; cost unacceptable |

## Known misses

Record a miss here with the case id, what the reviewer said instead, and why. Do not edit
a reviewer prompt to name the case; if a prompt change is warranted it must be a
class-level improvement that would also catch the variant's siblings.

- none recorded since redesign
