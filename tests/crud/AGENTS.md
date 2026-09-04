# CRUD tests

## Directory summary

These tests call `app.crud` directly with the shared SQLModel `Session`. They cover user password handling and lookup, authentication outcomes and role defaults, plus record/note creation and ORM relationships.

## Files and symbols

- `__init__.py` — marks `tests.crud` as a Python package; it defines no symbols.
- `test_record.py` — verifies record and note persistence and model relationships.
  - `test_create_record(db)` checks owner assignment, summary persistence, generated ID, and retrieval by primary key.
  - `test_record_belongs_to_user_relationship(db)` checks both `user.records` and `record.user` back-references.
  - `test_create_record_note(db)` checks note content, record association, and `record.notes` refresh behavior.
  - `test_random_record_note_creates_owner_chain(db)` ensures the convenience factory creates a note, record, and owning user when IDs are omitted.
- `test_user.py` — verifies password storage, authentication, roles, and lookup behavior.
  - `test_create_user_hashes_password(db)` ensures plaintext is not stored and the result uses the bcrypt `$2b$` prefix.
  - `test_authenticate_user(db)` accepts the correct email and password and returns the created user.
  - `test_authenticate_wrong_password(db)` returns `None` for an incorrect password.
  - `test_authenticate_unknown_user(db)` returns `None` for an unknown email.
  - `test_create_staff_user(db)` preserves an explicitly requested staff role.
  - `test_default_role_is_member(db)` checks the persisted user's `UserRole.member` default.
  - `test_get_user(db)` checks primary-key retrieval, JSON-equivalent model data, and `crud.get_user_by_email`.

These modules define no directory-local constants, fixtures, helpers, classes, methods, or nested functions. Every test receives the shared `db` session fixture defined by the parent test package.

## Test conventions

- Create independent data with `tests.utils` random factories so tests do not depend on execution order.
- Refresh SQLModel objects before asserting relationship collections populated after later writes.
- Keep authentication failure assertions non-enumerating: both a wrong password and an unknown user return `None` at this layer.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
