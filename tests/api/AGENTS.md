# API tests

## Directory summary

This package tests cross-route HTTP security properties. `test_authz_invariant.py` derives its coverage from the live OpenAPI schema so newly added authenticated GET operations under the versioned API prefix are checked automatically. Endpoint-specific behavior lives in `routes/` and has a more local guide.

## Files and symbols

- `__init__.py` — marks `tests.api` as a Python package; it defines no symbols.
- `test_authz_invariant.py` — probes every authenticated API GET path as each seeded member and rejects successful responses that expose another user's identifiers.
  - `EXEMPT_ROUTES` maps deliberately exempt route paths to their rationale. It is intentionally empty; any entry must represent explicit product behavior rather than a test workaround.
  - `SEEDED_MEMBER_EMAILS` contains the two member fixture emails used as callers.
  - `identifiers_owned_by(db, user)` returns the supplied user's ID and all record IDs owned by that user as strings.
  - `string_values(payload)` recursively collects every string value from JSON-like dictionaries and lists without depending on response field names.
  - `authenticated_get_routes()` reads `app.openapi()`, selects secured GET operations under `settings.API_V1_STR`, and returns each path with its path- and query-parameter names.
  - `test_member_never_receives_another_users_identifiers(client, db)` treats every other database user's user and owned-record IDs as foreign, substitutes them into every discovered path-parameter combination, supplies empty query values, and accumulates foreign identifiers found in HTTP 200 JSON responses.

## Child directories

- `routes/` — login, record, search, and vendor-preview endpoint tests; see its local `AGENTS.md`.

## Test conventions

- Keep the invariant schema-driven and resource-field agnostic. Extend identifier discovery when new user-owned models are added.
- Do not silently exempt a failing route. Documented exemptions are security policy and require explicit justification.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
