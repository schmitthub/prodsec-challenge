# Triage Write-Up

## Findings I would prioritize

| Priority | Finding | Severity | Rationale |
|---|---|---|---|
| P0 | Hardcoded `JWT_SECRET` and `verify_exp: False` (`app/auth.py:11`, `:34`) | Critical | The signing key is a string literal in a public repo, and expiry is disabled on verify. Anyone can mint a token for `user_clinician` (staff) that never expires and cannot be revoked. Every other auth control in the service depends on this. Fix: read the secret from a required env var and fail closed at startup; delete the `options=` kwarg so the 30-minute `exp` already issued is enforced. |
| P0 | Broken access control on `GET /api/records/{id}` and `GET /api/search` (`app/routes/records.py:22-33`, `app/routes/search.py`, `app/db.py:64`) | High | Both routes check only that the caller is authenticated. Any member reads any other member's record by ID; search is worse, an empty `q` matches `LIKE '%%'` and returns every released record for every user in one request. The correct guard already exists at `records.py:47` (404 on non-owner). Fix: apply that guard in `read_record`; pass `current_user.id` into `search_records` and filter on `owner_user_id` as a bound parameter in the SQL. This is the class the scenario calls out and no scanner in the pipeline sees it. |
| P1 | SSRF in `POST /api/webhooks/vendor-preview` (`app/routes/webhooks.py:25`) | High | Caller-supplied URL is fetched server-side and the status plus first 200 bytes of the body are returned, so this is a read oracle against cloud metadata and internal hosts, not a blind SSRF. Staff-only, but the P0 above makes staff free. Redirects are followed by default, so an input allowlist alone is bypassable. Fix: allowlist vendor hosts, `allow_redirects=False`, `trust_env=False`, stop echoing the body. |
| P1 | SQL injection in `search_records` (`app/db.py:75-78`) | Medium today, Critical pattern | Term is interpolated into the query. Impact is bounded right now: sqlite refuses stacked statements and the DB is a per-call in-memory copy, so an attacker gets unreleased rows and schema, nothing more. Fix anyway, it is one line and becomes Critical the day this points at a real database. Parameterize; do not "sanitize". Do this before adding the search owner filter or the filter is injectable too. |
| P1 | Exception detail leaked to clients (`app/main.py:26`) | Medium | `repr(exc)` is returned on every unhandled error to unauthenticated callers. It turns the SQLi above from blind to error-based and leaks paths and library internals. Fix: log server-side with a request ID, return a generic body. |
| P2 | Container runs as root (`Dockerfile`, no `USER`) | Medium | Not exploitable alone; multiplies any code-execution bug. Fix: add a non-root user. |
| P2 | Vendor API key committed (`config/dev.py:1`) | Medium | Seeded value, but `fh_live_` prefix means rotate first and ask later. Move to env var. |
| P2 | Dependency gate is red: pyjwt 2.12.0 (PYSEC-2026-179, 7.4) and starlette 0.50.0 (PYSEC-2026-2281 / -249, 7.5) exceed the 7.0 image-scan threshold; requests 2.31.0 carries three lower advisories | Medium | None of the 13 advisories is reachable in this codebase (no JWKS client, no asymmetric algorithms, no `Session`, no `StaticFiles`, no form parsing). Patch per package, not per advisory: pyjwt → 2.13.0 and requests → 2.33.0 are drop-in. Starlette cannot move because `fastapi==0.128.0` pins `starlette<0.51.0`; clearing it needs fastapi 0.141.1 plus a starlette 1.x bump in its own tested PR. PYSEC-2026-179 is the one to watch: adding an asymmetric algorithm next to the already-public HMAC secret would make it live. |

## False positives and acceptable in context

- `helpers/fixture_secrets.py:7` — False positive. Fixture value, never imported by `app/` or `tests/`, gated behind a test-env check. Recommendation is still to remove it and generate keys inside the test harness; a committed placeholder is how a real secret lands in the repo by accident.
- `app/routes/login.py:18` non-constant-time compare — Informational. The delta is nanoseconds against milliseconds of network jitter, and both branches return the same 401. Not actionable on its own.
- Requests `.netrc` advisory (PYSEC-2026-1872) — not a separate finding. It is the same SSRF path at `webhooks.py:25` and closes with the requests bump.
- 12 of 13 package advisories are unreachable today; they are patched because the gate is red and the bump is cheap, not because they are exploitable here.

## What the pipeline catches

Semgrep blocks on the hardcoded JWT secret, the SQL interpolation, the SSRF call, and the root container. Gitleaks blocks on the vendor key via a repo-specific rule (default rules miss the format). Bandit reports the secret and the SQLi below its HIGH gate and only surfaces them in Code scanning. The image scan blocks on pyjwt and starlette at the 7.0 threshold. Dependency review blocks High+ advisories on changed dependencies.

## What the pipeline does not catch

`verify_exp: False` and the `repr(exc)` leak. `JWT_SECRET` also escapes gitleaks because it is low-entropy English. Bandit's HIGH-only gate means its MEDIUM SQLi finding never blocks.

Off-the-shelf SAST does not model "this object has an owner that must match the caller", and pattern rules for it drown in false positives as routes grow. The custom check is a cross-user identifier invariant test (`tests/test_authz_invariant.py`): it walks every authenticated GET route from the OpenAPI schema, calls it as each member with other users' identifiers (user ids and the ids of records they own) in path params and empty query values, and fails if any 200 body contains an identifier that belongs to someone else. It matches values, not field names, so it needs no knowledge of the resource shape and covers user objects and future resources as well as records. It asserts nothing about staff; staff-only routes return 403 to a member and are skipped. It fails today on both seeded BAC routes and catches any future route that returns another user's data unscoped, whether the leak comes from a path ID, a query, or a missing filter.

## Where I would invest next

Password hashing (`db.USERS` stores plaintext), rate limiting on `/api/login`, a shared authorization dependency so ownership checks cannot be forgotten per route, retiring `requirements.txt` so the image installs from `uv.lock` (today the scanned artifact and the shipped artifact differ), and a CI check that fails if an asymmetric JWT algorithm is ever added alongside HS256.
