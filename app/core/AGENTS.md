# `app/core/`

## Directory summary

Shared infrastructure for environment-backed application settings, the SQLModel engine and local fixture seeding, password hashing, and JWT issuance. API dependencies and lifecycle entry points import these modules; this package does not declare HTTP routes.

## Role in the project

`config.py` materializes and validates settings at import time. `db.py` creates the shared PostgreSQL engine and seeds local-only fixtures through `app.crud`. `security.py` supplies bcrypt and HS256 primitives used by authentication and user creation. Database schema ownership remains in `app/alembic/`; `db.py` does not create tables.

## Files and symbols

### `__init__.py`

Package marker; it defines no code symbols.

### `config.py`

Defines parsing helpers and the environment-backed `Settings` model.

- `parse_cors(v)`: Before-validation helper that splits a non-JSON comma-separated string into stripped, non-empty entries, passes lists and bracketed strings through for Pydantic to handle, and rejects every other input type with `ValueError`.
- `Settings`: `BaseSettings` subclass containing all service configuration and post-validation rules.
  - `model_config`: Reads `.env`, ignores empty environment values, and ignores extra keys.
  - `API_V1_STR`: API prefix, defaulting to `/api/v1`.
  - `SECRET_KEY`: JWT signing secret with a fresh `secrets.token_urlsafe(32)` default.
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: Access-token lifetime in minutes, defaulting to `30`.
  - `ENVIRONMENT`: Deployment mode restricted to `local`, `staging`, or `production`; defaults to `local`.
  - `SEED_PASSWORD`: Required password shared by accounts created during local fixture seeding.
  - `BACKEND_CORS_ORIGINS`: CORS origin list, or pre-parse string, normalized through `parse_cors`; defaults to an empty list.
  - `all_cors_origins`: Computed property returning configured CORS origins as strings without trailing slashes.
  - `LAB_VENDOR_API_KEY`: Required vendor API credential setting.
  - `DEBUG_VENDOR_URL`: Required vendor/debug URL setting.
  - `WEBHOOK_ALLOWED_HOSTS`: Webhook destination host list, or pre-parse string, normalized through `parse_cors`; an empty list denies all preview destinations.
  - `webhook_allowed_hosts`: Computed property returning non-empty configured hosts stripped and lowercased in a `frozenset` for exact matching.
  - `PROJECT_NAME`: Required service display name.
  - `POSTGRES_SERVER`: Required PostgreSQL hostname.
  - `POSTGRES_PORT`: PostgreSQL port, defaulting to `5432`.
  - `POSTGRES_USER`: Required PostgreSQL username.
  - `POSTGRES_PASSWORD`: PostgreSQL password, defaulting to an empty string.
  - `POSTGRES_DB`: PostgreSQL database name, defaulting to an empty string.
  - `SQLALCHEMY_DATABASE_URI`: Computed `PostgresDsn` built with the `postgresql+psycopg` scheme and the configured PostgreSQL fields.
  - `_check_default_secret(var_name, value)`: Warns when a checked value is empty locally and raises `ValueError` when it is empty in staging or production.
  - `_enforce_non_default_secrets()`: After-model validator applying `_check_default_secret` to `SECRET_KEY`, `POSTGRES_PASSWORD`, and `SEED_PASSWORD`, then returning the validated settings object.
- `settings`: Import-time singleton `Settings` instance consumed throughout the application.

### `db.py`

Creates the shared SQLModel engine and provides idempotent, local-only fixture seeding.

- `engine`: Shared SQLAlchemy engine created from the string form of `settings.SQLALCHEMY_DATABASE_URI`.
- `SEED_USERS`: Local fixture dictionaries for Alice and Bob as members and the clinician as staff; `_get_or_create_user` supplies `settings.SEED_PASSWORD` when creating them.
- `SEED_RECORDS`: Local fixture dictionaries keyed by `owner_email`; each carries a record `type`, `status`, `summary`, and list of note strings for Alice's A1C and Bob's LDL records.
- `_get_or_create_user(session, email=, role=)`: Returns the first user with the email or creates one through `crud.create_user` with the configured seed password.
- `_get_or_create_record(session, owner=, type=, status=, summary=)`: Returns the first record matching `(owner.id, summary)` or creates one through `crud.create_record`.
- `_get_or_create_note(session, record=, note=)`: Returns the first note matching `(record.id, note)` or creates one through `crud.create_record_note`.
- `init_db(session)`: Returns without changes outside the local environment; locally, maps seeded users by email, then idempotently creates all configured records and notes through the natural-key helpers. Tables must already exist through Alembic migrations.

### `security.py`

Password hashing/verification and access-token issuance primitives.

- `ALGORITHM`: JWT signing algorithm, `HS256`.
- `create_access_token(subject, expires_delta)`: Creates a signed JWT containing string `sub` and an absolute UTC `exp` claim.
- `verify_password(plain_password, hashed_password)`: Verifies an encoded plaintext password against a bcrypt hash.
- `get_password_hash(password)`: Generates a bcrypt salt and returns the resulting hash as text.
