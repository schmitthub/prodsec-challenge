# Evaluation cases

Run `sec-review --full` and compare `result.json` to this list. Record hits, misses, and
false positives in the report footer. Do not tune the reviewers until a miss stops being a
miss — record it in `challenge/triage.md` §"what the pipeline does not catch" instead.

## Expected detections (seeded)

| id | class | where | expected severity | deterministic evidence available? |
|---|---|---|---|---|
| S1 | access-control | `app/routes/records.py` `read_record` — no owner check on `GET /api/records/{record_id}` | high | no scanner; TestClient repro (bob reads alice's record → 200); negative-authz test in `tests/` if present |
| S2 | access-control | `app/routes/search.py` — results not filtered to caller | high | TestClient repro |
| S3 | injection | `app/db.py` `search_records` — f-string SQL | critical | semgrep/bandit hit; repro with `q=' OR 1=1 --` |
| S4 | injection | `app/routes/webhooks.py` — outbound GET to caller URL, no allowlist | high | semgrep/CodeQL taint; repro to `http://127.0.0.1:8000/health` |
| S5 | authn-secrets | `app/auth.py` hardcoded `JWT_SECRET` | high | gitleaks/semgrep hit |
| S6 | authn-secrets | `app/auth.py` `verify_exp: False` | high | semgrep hit if rule present, else reasoning |
| S7 | authn-secrets | `app/db.py` `USERS` plaintext passwords | high | bandit B105/B106 maybe; reasoning |
| S8 | data-exposure | `app/main.py` global handler returns `repr(exc)` | medium | semgrep maybe; repro by forcing an exception |
| S9 | data-exposure | `app/routes/webhooks.py` echoes upstream response | high | repro |
| S10 | supply-chain-ci | `Dockerfile` runs as root | medium | `grep -c '^USER' Dockerfile` = 0 |
| S11 | supply-chain-ci | `requirements.txt` vs `uv.lock` — two dep surfaces | medium | diff of pins |

## Expected non-detections

| id | where | why it must not be flagged | which kill test |
|---|---|---|---|
| N1 | `GET /api/me` | no client-supplied id | reviewer scope |
| N2 | `GET /api/records/{id}/notes` | owner check present | `control-exists` |
| N3 | `POST /api/webhooks/vendor-preview` staff gate | role gate on a staff-wide action (SSRF is a separate, real finding) | `intended-shared-resource` for access-control only |
| N4 | `tests/test_records.py` credentials | fixture creds for fake DB | `test-or-fixture-code` |
| N5 | `helpers/fixture_secrets.py`, `config/dev.py` contents | redacted; only "file changed, review manually" allowed | redaction |
| N6 | `test.yml` minimal workflow | seeded, out of scope by policy | reviewer scope |
| N7 | SHA-pinned actions | correct pattern | reviewer scope |

## Variant probes (not in the tree — write to scratchpad, run `--full` against a throwaway branch)

Use these to answer "what would your check catch that we didn't seed". Each is a small
edit to a copy of `app/routes/records.py`:

| id | variant | expected |
|---|---|---|
| V1 | `DELETE /api/records/{record_id}` no check | access-control, critical |
| V2 | `GET /api/records?id=<x>` query param instead of path | access-control, high |
| V3 | lookup via helper `db.get_record(record_id)` in `app/db.py` | access-control, high (confidence may drop to medium — helper in another file) |
| V4 | `if body.role == "staff": return RECORDS[record_id]` | access-control, critical (identity from request) |
| V5 | `if user.role != "staff" or record["owner_id"] != user.id: raise 403` (inverted logic) | **expected miss** for static reviewers; repro should catch it — document as a known limit |
| V6 | new `/api/invoices/{invoice_id}` not in `auth-model.md` | access-control, medium, "declaration missing" |
| V7 | `PATCH /api/records/{id}` writing `body.owner_id` into the record | access-control, critical (mass assignment) |

## Scoring

- hit = expected detection present with correct class and severity within one step.
- miss = expected detection absent after verify.
- FP = anything surviving verify that is in the non-detection list, or that a human rejects.
- Report `hits/expected`, `misses`, `FPs`, and verifier kill counts by `false_positive_kind`.
