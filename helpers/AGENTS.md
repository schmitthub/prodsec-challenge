# `helpers/`

## Directory summary

Test-only Python support code. This directory provides isolated fixture values and rejects accidental use from a non-test process. It has no child directories.

## Role in the project

`helpers/` supports the test suite rather than the runtime application. It is not an importable Python package because it has no `__init__.py`.

## Files and symbols

- `fixture_secrets.py` — Defines a test-only JWT secret and raises `RuntimeError` unless `PYTEST_CURRENT_TEST` is set or `APP_ENV=test`.
  - `FIXTURE_JWT_SECRET` — Stable JWT signing secret for unit-test fixtures; never intended for runtime use.
