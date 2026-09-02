# Tests

## Directory summary

Python `unittest` coverage for the FastAPI records service. The suite exercises basic health and member record behavior, plus a route-discovery invariant that detects cross-user identifier exposure. This directory has no child source directories.

## Test modules and symbols

### `test_authz_invariant.py`

Discovers authenticated `GET` routes from the app's OpenAPI schema and checks that member responses never expose identifiers owned by another user.

- `client`: shared FastAPI `TestClient` used by the module.
- `EXEMPT_ROUTES`: documented allowlist for routes intentionally permitted to return cross-user identifiers; empty by default.
- `login(email, password)`: authenticates a fixture user and returns its bearer token.
- `identifiers_owned_by(user_id)`: collects a user's id and the ids of records they own.
- `string_values(payload)`: recursively extracts string values from JSON-compatible response data.
- `authenticated_get_routes()`: returns authenticated API `GET` paths and their path/query parameter names from OpenAPI.
- `CrossUserIdentifierInvariant`: authorization-invariant test case.
  - `test_member_never_receives_another_users_identifiers()`: probes each discovered route as every member using foreign identifiers and reports successful responses that leak them.

### `test_records.py`

Provides focused happy-path API tests for service health and member-owned records.

- `client`: shared FastAPI `TestClient` used by the module.
- `login(email, password)`: authenticates a fixture user and returns its bearer token.
- `auth_headers(token)`: builds the bearer authorization header for API requests.
- `RecordsApiTests`: core records API test case.
  - `test_health_check()`: verifies `/health` returns the expected success payload.
  - `test_member_can_list_their_records()`: verifies Alice sees her single record in the records collection.
  - `test_member_can_read_their_record_notes()`: verifies Alice can retrieve notes for her own record.
