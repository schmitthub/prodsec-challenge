# Baseline: findings already tracked

Maintained by hand. Project-owned record of security findings the team has already
triaged. The verifier consults it; reviewers must not (see `reviewers/_common.md`).

A baselined finding is still real and still reported, but the decision is `comment`, not
`block`: it is not a regression introduced by the change under review. Remove an entry when
the finding is fixed. Add an entry only with a status and a reason.

| id | class | where | status | reason |
|---|---|---|---|---|
| B1 | access-control | `app/routes/records.py` `read_record`: no owner check on `GET /api/records/{record_id}` | tracked, intentionally unpatched | seeded defect; subject of the exercise per `AGENTS.md` |
| B2 | access-control | `app/routes/search.py` `search`: results not filtered to caller | tracked, intentionally unpatched | seeded defect |
| B3 | injection | `app/db.py` `search_records`: query built with an f-string | tracked, intentionally unpatched | seeded defect |
| B4 | outbound-requests | `app/routes/webhooks.py` `vendor_preview`: outbound GET to caller-supplied URL, response echoed | tracked, intentionally unpatched | seeded defect |
| B5 | secrets-crypto | `app/auth.py` `JWT_SECRET` literal | tracked, intentionally unpatched | seeded defect |
| B6 | authentication | `app/auth.py` `verify_exp: False` | tracked, intentionally unpatched | seeded defect |
| B7 | authentication | `app/db.py` `USERS` plaintext passwords | tracked, intentionally unpatched | seeded defect |
| B8 | data-exposure | `app/main.py` global handler returns `repr(exc)` | tracked, intentionally unpatched | seeded defect |
| B9 | supply-chain-ci | `Dockerfile` runs as root | tracked | low standalone impact; fix pending |
| B10 | supply-chain-ci | `requirements.txt` vs `uv.lock` two dependency surfaces | tracked | retiring `requirements.txt` is a documented recommendation |
| B11 | secrets-crypto | `config/dev.py`, `helpers/fixture_secrets.py` fixture values | accepted | fake, non-production values; redacted from the pack; in the gitleaks baseline |
| B12 | authentication | `app/routes/login.py` non-constant-time password compare | accepted, informational | not network-exploitable here; same 401 on both branches |
| B13 | data-exposure | `/docs`, `/redoc`, `/openapi.json` unauthenticated | accepted | framework default for a dev service |

## Other baseline sources

- `gitleaks-report.json` (redacted): secret-scanner baseline. Every consumer passes `--redact`.
- `osv-scanner.toml`: dependency ignores; each entry must carry `reason` and `ignoreUntil`.
