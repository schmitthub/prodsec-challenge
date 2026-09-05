# Tests

## Directory summary

This package is the pytest suite for the FastAPI records service. Tests use the application-level `TestClient` and a real SQLModel session backed by `app.core.db.engine`; the configured PostgreSQL database must be available. Session setup seeds the standard local users, and teardown deletes test notes, records, and users.

Run the supported test entry point with `uv run bash scripts/tests-start.sh`. It waits for the database through `app.tests_pre_start`, runs `coverage run -m pytest tests/`, prints the coverage report, and writes HTML coverage output. A focused module can be run with `uv run pytest tests/path/to/test_module.py` when the database is already ready.

## Files and symbols

- `__init__.py` — marks `tests` as a Python package; it defines no symbols.
- `conftest.py` — owns suite-wide database, client, and authentication fixtures.
  - `MEMBER_EMAIL`, `OTHER_MEMBER_EMAIL`, and `STAFF_EMAIL` identify the seeded Alice, Bob, and clinician accounts.
  - `db` is an autouse, session-scoped `Session` fixture. It calls `init_db`, yields the shared session, then deletes `RecordNote`, `Record`, and `User` rows in dependency order.
  - `client` is a module-scoped `TestClient` fixture for `app.main.app`.
  - `member_token_headers`, `other_member_token_headers`, and `staff_token_headers` are module-scoped bearer-header fixtures for the three seeded accounts.

## Child directories

- `authz/` — database-independent reusable-contract tests; see `authz/AGENTS.md`.
- `scanners/` — scanner gate and suppression audit tests; see `scanners/AGENTS.md`.
- `api/` — HTTP behavior and the route-discovery authorization invariant; see its local `AGENTS.md`.
- `crud/` — direct persistence, authentication, hashing, and model-relationship tests; see its local `AGENTS.md`.
- `scripts/` — isolated tests for the database-readiness entry points; see its local `AGENTS.md`.
- `utils/` — reusable user, token, record, note, and random-data factories; see its local `AGENTS.md`.

## Test conventions

- Prefer fresh users and records from `tests.utils` when a test mutates state. Reserve the seeded accounts for stable authentication and cross-user scenarios.
- Assert both status codes and security-relevant response shape: ownership scoping, error consistency, omitted secrets, and whether an outbound call occurred.
- Outbound HTTP must be monkeypatched. Tests must not rely on network access.
- Keep fixture cleanup compatible with PostgreSQL foreign-key order and keep local test guides synchronized when files or symbols change.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
