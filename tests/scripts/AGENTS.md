# Pre-start script tests

## Directory summary

These focused, mirror-image tests exercise the callable database-readiness helpers used by the backend and test startup entry points. Each test mocks the Session symbol used by its module, invokes `init`, and verifies that the supplied engine executes exactly one `SELECT 1` statement.

## Files and symbols

- `__init__.py` — marks `tests.scripts` as a Python package; it defines no symbols.
- `test_backend_pre_start.py` — tests `app.backend_pre_start.init`.
  - `test_init_successful_connection()` mocks the engine and context-managed session; patches `app.backend_pre_start.Session`; verifies the engine argument, one execution, and SQL expression equality with `select(1)`. Exceptions fail the test directly.
- `test_test_pre_start.py` — tests `app.tests_pre_start.init`.
  - `test_init_successful_connection()` performs the same checks against `app.tests_pre_start.Session`.

These modules define no directory-local constants, reusable helpers, fixtures, classes, methods, or nested functions.

## Test conventions

- Keep the two modules structurally aligned because they cover equivalent backend and test startup helpers.
- When strengthening these tests, patch the symbol resolved by the module under test (`app.backend_pre_start.Session` or `app.tests_pre_start.Session`) and use `assert_called_once_with` for call verification.
- Keep these unit tests connection-free; integration with PostgreSQL is exercised by the real startup and broader test suite.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
