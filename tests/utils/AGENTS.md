# `tests/utils/`

## Directory summary

This package supplies random-data, authentication, user, record, and note factories shared by database and route tests. Persistence factories use `app.crud` rather than reproducing SQLModel write details in individual tests, while token helpers authenticate through the public OAuth2 login route.

## Files and symbols

- `__init__.py` — marks `tests.utils` as a Python package; it defines no symbols.
- `utils.py` — provides primitive random values and the HTTP login helper.
  - `random_lower_string()` returns a 32-character lowercase ASCII string.
  - `random_email()` combines two random lowercase strings into a `.com` email address.
  - `login_token_headers(client, *, email, password)` posts an OAuth password-grant form to the versioned login endpoint, asserts a 200 response, and returns an `Authorization: Bearer` header containing the response token.
- `user.py` — creates users and authentication headers for fresh or seeded accounts.
  - `create_random_user(db, *, role=UserRole.member)` delegates to the credential-returning factory, discards the generated plaintext password, and returns the persisted user.
  - `create_random_user_with_password(db, *, role=UserRole.member)` creates a random `UserCreate` through `crud.create_user` and returns both the persisted user and its generated password.
  - `random_user_token_headers(*, client, db, role=UserRole.member)` creates a fresh user and returns it with bearer headers obtained through the real login endpoint.
  - `seed_user_token_headers(*, client, email)` logs in a seeded fixture account with `settings.SEED_PASSWORD` and returns bearer headers.
- `record.py` — creates released lab-result records and their notes for persistence and API tests.
  - `create_random_record(db, *, user_id=None, summary=None)` creates an owner when `user_id` is omitted, defaults the summary to random text, fixes the type and status to `lab_result` and `released`, and persists through `crud.create_record`.
  - `create_random_record_note(db, *, record_id=None)` creates a record and owner chain when `record_id` is omitted, generates random note text, and persists through `crud.create_record_note`.

These modules define no directory-local constants, classes, methods, fixtures, test functions, or nested helpers. The nine functions above are the complete direct code-symbol inventory.

## Utility conventions

- Keep helpers deterministic in shape but random in identity so callers can safely share the session without collisions.
- Return credentials only from helpers whose names explicitly promise them; `create_random_user` intentionally discards its password.
- Authenticate through the public login route when producing bearer headers so route tests cover the deployed token format.
- Add reusable test factories here only when multiple test modules need them; endpoint-specific helpers belong beside their tests.

## Local guide aliases

- `AGENTS.md` — this directory-scoped contributor guide.
- `CLAUDE.md` — portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
