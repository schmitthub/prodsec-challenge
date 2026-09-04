# Tests

## Directory summary

`pytest` suite for the FastAPI records service, run against the real Postgres engine (`app.core.db.engine`), so it needs the compose `db` service or an equivalent `POSTGRES_*` environment. `conftest.py` seeds the local fixture accounts via `init_db` once per session and wipes `recordnote`, `record` and `user` on teardown. Layout follows the full-stack-fastapi-template shape: `api/routes/` for HTTP behaviour, `crud/` for the data layer, `scripts/` for the pre-start helpers, `utils/` for factories.

Run inside the compose backend container (the image does not include `tests/` or `scripts/test*.sh`):

```bash
docker compose run --rm -v "$PWD/app:/app/app" -v "$PWD/tests:/app/tests" -v "$PWD/scripts:/app/scripts" backend bash scripts/tests-start.sh
```

## Fixtures (`conftest.py`)

- `db` (session, autouse): SQLModel `Session` on the app engine; runs `init_db`, cleans up afterwards.
- `client` (module): `TestClient(app)`.
- `member_token_headers` / `other_member_token_headers` / `staff_token_headers` (module): bearer headers for the seeded `alice`, `bob` and `clinician` accounts, logged in with `settings.SEED_PASSWORD`.
- `MEMBER_EMAIL`, `OTHER_MEMBER_EMAIL`, `STAFF_EMAIL`: the seeded account emails.

## Helpers (`utils/`)

- `utils.py` — `random_lower_string`, `random_email`, `login_token_headers(client, email=, password=)` (form-encoded password grant, asserts 200).
- `user.py` — `create_random_user(db, role=)`, `create_random_user_with_password(db, role=)`, `random_user_token_headers(client=, db=, role=)` → `(User, headers)`, `seed_user_token_headers(client=, email=)`.
- `record.py` — `create_random_record(db, user_id=, summary=)`, `create_random_record_note(db, record_id=)`; both create the owner chain when ids are omitted.

## Test modules

- `api/routes/test_login.py` — seeded and random login, wrong password and unknown user both 401 with the same detail, `/me` with a valid token, no token 401, garbage token 403.
- `api/routes/test_records.py` — `/health`; `/records` list is scoped to the caller with `count`, pagination, 401 unauthenticated; `/records/{id}` own 200, foreign and missing 404, bad uuid 422; `/records/{id}/notes` own 200 with `record_id`/`data`/`count`, foreign 404, staff can read any, staff missing 404, unauthenticated 401.
- `api/routes/test_search.py` — case-insensitive substring match on own summaries only, `%`/`_` treated literally, pagination, `q` missing/empty/too long 422, unauthenticated 401.
- `api/routes/test_webhooks.py` — `requests.get` is monkeypatched so nothing leaves the process. Allowed host comes from `settings.webhook_allowed_hosts` (`WEBHOOK_ALLOWED_HOSTS` env, required non-empty). Member 403 and unauthenticated 401 make no outbound call; staff on an allowed https host gets `status_code`/`content_type`/`preview[:200]`, the fetch uses `timeout=2` and `allow_redirects=False`, host match is case-insensitive; unlisted hosts, loopback/metadata IPs, subdomains of an allowed host and plain http are 400 with no fetch; upstream `RequestException` is reported as `status_code: 500` in the body; malformed/empty/null `callback_url` 422.
- `api/test_authz_invariant.py` — discovers every authenticated GET route under `API_V1_STR` from OpenAPI, calls each as both seeded members with every foreign user/record id in path params, and fails if any 200 body contains a foreign identifier. `EXEMPT_ROUTES` is the documented allowlist; keep it empty.
- `crud/test_user.py` — bcrypt hashing, authenticate success/wrong password/unknown, role default and staff, get by id and email.
- `crud/test_record.py` — create record with owner, relationship back-refs, create note, factory owner chain.
- `scripts/test_backend_pre_start.py`, `scripts/test_test_pre_start.py` — mocked engine check for the retry helpers.
