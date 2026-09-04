# `tests/api/routes/`

## Directory summary

Endpoint-level pytest coverage for the public FastAPI surface. These modules exercise OAuth2 login and bearer authentication, owner-scoped record and search reads, record-note authorization, and the staff-only vendor-preview boundary through `TestClient`. Database-backed tests use the shared session and authentication fixtures from `tests/conftest.py` plus factories from `tests/utils/`; webhook tests replace the outbound request function so the suite never performs network I/O.

## Role in the project

Each module mirrors behavior owned by the corresponding module under `app/api/routes/`. The tests preserve security contracts at the HTTP boundary: credential failures do not enumerate users, foreign records look absent, search results remain caller-scoped, and rejected webhook requests do not trigger an outbound call. Cross-route authorization discovery remains in the parent `tests/api/test_authz_invariant.py` module.

## Files and symbols

- `__init__.py` — marks `tests.api.routes` as a Python package; it defines no code symbols.
- `test_login.py` — verifies token issuance, form validation, indistinguishable credential failures, bearer authentication, and OpenAPI's password-flow declaration.
  - `LOGIN` is the versioned login path built from `settings.API_V1_STR`.
  - `_form(email, password, **extra)` builds an OAuth password-grant form payload; `extra` values can override the default `grant_type` for rejection tests.
  - `test_login_seed_user(client)` checks the seeded member's bearer token, expiry metadata, and no-cache headers.
  - `test_login_random_user(client, db)` authenticates a freshly created database user.
  - `test_login_grant_type_is_optional(client)` permits omission of `grant_type`.
  - `test_login_rejects_other_grant_types(client)` rejects a non-password grant.
  - `test_login_rejects_json_body(client)` requires form encoding.
  - `test_login_incorrect_password(client)` checks the OAuth `invalid_grant` response and cache header.
  - `test_login_unknown_user_same_error_as_bad_password(client)` preserves the non-enumerating credential error.
  - `test_use_access_token(client, member_token_headers)` reads `/me` and ensures `hashed_password` is absent.
  - `test_me_without_token(client)` expects authentication to be required.
  - `test_me_with_garbage_token(client)` rejects an invalid bearer token.
  - `test_openapi_declares_password_flow_at_login(client)` checks the `Bearer` password flow's `tokenUrl`.
- `test_records.py` — verifies health, caller-owned record listing and reads, pagination, UUID validation, record-note authorization, and staff note access.
  - `test_health_check(client)` checks the unauthenticated health response.
  - `test_list_my_records(client, db)` ensures list data and count contain only the caller's records.
  - `test_list_records_pagination(client, db)` checks `skip` and `limit` while retaining the total count.
  - `test_list_records_unauthenticated(client)` requires authentication for the collection.
  - `test_read_own_record(client, db)` checks the complete ownership-sensitive record response.
  - `test_read_other_users_record_is_not_found(client, db)` hides a foreign record behind the same 404 used for absence.
  - `test_read_record_missing(client, db)` checks a nonexistent UUID.
  - `test_read_record_invalid_id(client, db)` checks request validation for a malformed UUID.
  - `test_read_own_record_notes(client, db)` checks the note envelope, IDs, count, and record association.
  - `test_read_other_users_record_notes_is_not_found(client, db)` hides foreign notes behind a 404.
  - `test_staff_can_read_any_record_notes(client, db)` verifies the staff-role exception to ownership.
  - `test_staff_record_notes_missing(client, db)` preserves 404 behavior for staff when the record is absent.
  - `test_read_record_notes_unauthenticated(client, db)` requires authentication for notes.
- `test_search.py` — verifies caller-scoped, case-insensitive literal substring search and its validation and pagination behavior.
  - `_search(client, headers, q, **params)` issues a versioned search request with the required query and optional pagination parameters.
  - `test_search_matches_own_summary_case_insensitively(client, db)` checks a single own-record hit independent of case.
  - `test_search_is_scoped_to_caller(client, db)` excludes another user's matching record.
  - `test_search_like_metacharacters_are_literal(client, db)` ensures `%` and `_` do not become SQL wildcards.
  - `test_search_pagination(client, db)` checks paginated data length and the unpaginated total count.
  - `test_search_requires_query(client, db)` rejects missing, empty, and overlong queries.
  - `test_search_unauthenticated(client)` requires authentication.
- `test_webhooks.py` — tests authorization, callback validation, exact host allowlisting, safe request options, bounded previews, and upstream failures without making network calls.
  - `URL` is the versioned vendor-preview endpoint built from `settings.API_V1_STR`.
  - `allowed_url()` is a module-scoped fixture that derives an HTTPS URL from the first configured allowed webhook host and fails if none is configured.
  - `_host(url)` extracts the host from the controlled HTTPS fixture URL.
  - `_FakeResponse` models the response attributes consumed by the route.
    - `_FakeResponse.__init__(status_code=, text=, content_type=)` records status and text and creates the lowercase content-type header mapping.
  - `outbound_calls(monkeypatch)` is a per-test fixture that records request arguments, replaces `webhooks.requests.get`, and returns the mutable call list.
    - `fake_get(url, **kwargs)` is its nested request stub; it records each call and returns a deterministic 200 response with 500 characters of plain text.
  - `test_member_is_forbidden(client, member_token_headers, outbound_calls, allowed_url)` rejects members before an outbound call.
  - `test_unauthenticated_is_rejected(client, outbound_calls, allowed_url)` rejects missing credentials before an outbound call.
  - `test_staff_preview_allowed_host(client, staff_token_headers, outbound_calls, allowed_url)` checks the response projection, 200-character preview limit, two-second timeout, and disabled redirects.
  - `test_staff_preview_allowed_host_is_case_insensitive(client, staff_token_headers, outbound_calls, allowed_url)` accepts case variation in an allowed hostname and performs exactly one request.
  - `test_staff_preview_disallowed_host(client, staff_token_headers, outbound_calls, callback_url)` parametrically rejects an unlisted host, loopback address, link-local metadata address, and localhost without fetching.
  - `test_staff_preview_lookalike_hosts_are_rejected(client, staff_token_headers, outbound_calls, allowed_url)` rejects both subdomain and suffix lookalikes of an allowed hostname without fetching.
  - `test_staff_preview_requires_https(client, staff_token_headers, outbound_calls, allowed_url)` rejects plain HTTP without fetching.
  - `test_staff_preview_reports_upstream_failure(client, staff_token_headers, monkeypatch, allowed_url)` checks the route's projected failure response when the HTTP client raises a connection error.
    - `failing_get(*_args, **_kwargs)` is its nested request stub; it raises a deterministic `requests.ConnectionError`.
  - `test_invalid_callback_url_is_rejected(client, staff_token_headers, outbound_calls, bad)` parametrically rejects malformed, unsupported-scheme, empty, and null callback values without fetching.

## Test conventions

- Use `settings.API_V1_STR` for API paths; `/health` and `/api/v1/openapi.json` are intentional exceptions.
- For authorization failures, assert that protected operations have no side effect, especially no outbound request.
- Keep request stubs attached to `app.api.routes.webhooks.requests`, the object used by the route under test.
- Preserve indistinguishable 404 responses for missing and foreign records, and preserve non-enumerating login errors.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
