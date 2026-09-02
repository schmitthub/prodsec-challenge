# `helpers/`

## Directory summary

Test-only Python support code. This directory provides isolated fixture values and rejects accidental use from a non-test process. It has no child directories.

## Role in the project

`helpers/` supports the test suite rather than the runtime application. It is not an importable Python package because it has no `__init__.py`.

## Files and symbols

- `fixture_secrets.py` — Defines a test-only JWT secret and raises `RuntimeError` when imported outside pytest or an `APP_ENV=test` process.
  - `FIXTURE_JWT_SECRET` — Stable JWT signing secret for unit-test fixtures; never intended for runtime use.
