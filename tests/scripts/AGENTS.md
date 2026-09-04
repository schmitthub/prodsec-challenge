# Pre-start script tests

## Directory summary

These focused, mirror-image tests exercise the callable database-readiness helpers used by the backend and test startup entry points. Each test builds mock engine, session, and execution objects, suppresses the imported module logger's output, and checks that calling `init` does not raise.

## Files and symbols

- `__init__.py` — marks `tests.scripts` as a Python package; it defines no symbols.
- `test_backend_pre_start.py` — tests `app.backend_pre_start.init`.
  - `test_init_successful_connection()` constructs `engine_mock`, `session_mock`, and `exec_mock`; patches `sqlmodel.Session` plus the imported backend logger's `info`, `error`, and `warn` methods; records whether `init(engine_mock)` raises; asserts the successful-call flag; and evaluates `session_mock.exec.called_once_with(select(1))`. Note that `called_once_with` is not unittest.mock's asserting `assert_called_once_with` API, so this expression does not currently prove the call count or arguments.
- `test_test_pre_start.py` — tests `app.tests_pre_start.init`.
  - `test_init_successful_connection()` constructs `engine_mock`, `session_mock`, and `exec_mock`; patches `sqlmodel.Session` plus the imported test-start logger's `info`, `error`, and `warn` methods; records whether `init(engine_mock)` raises; asserts the successful-call flag; and evaluates `session_mock.exec.called_once_with(select(1))`. As in the backend test, that mock expression is non-asserting.

These modules define no directory-local constants, reusable helpers, fixtures, classes, methods, or nested functions.

## Test conventions

- Keep the two modules structurally aligned because they cover equivalent backend and test startup helpers.
- When strengthening these tests, patch the symbol resolved by the module under test (`app.backend_pre_start.Session` or `app.tests_pre_start.Session`) and use `assert_called_once_with` for call verification.
- Keep these unit tests connection-free; integration with PostgreSQL is exercised by the real startup and broader test suite.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
