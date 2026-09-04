# `app/`

## Directory summary

The runtime package for the FastAPI records service. It assembles the ASGI application, defines the SQLModel database and API schemas, implements persistence helpers, and provides database readiness and seed-data entry points. HTTP dependencies and routers live under `api/`, shared configuration and infrastructure live under `core/`, and schema migrations live under `alembic/`; each child source directory has its own guide.

## Role in the project

`main.py` is the Uvicorn entry point and mounts `api.main.api_router` at the configured API prefix. Route handlers exchange the models in `models.py`, use sessions supplied by `api.deps`, and call the persistence operations in `crud.py`. `backend_pre_start.py`, `tests_pre_start.py`, and `initial_data.py` are executable lifecycle helpers used around application and test startup.

## Child directories

- `api/` — shared FastAPI dependencies, top-level API router composition, and endpoint modules; see `api/AGENTS.md`.
- `core/` — settings, database engine and local seed data, and password/JWT primitives; see `core/AGENTS.md`.
- `alembic/` — Alembic runtime configuration, revision template, and migration revisions; see `alembic/AGENTS.md`.

## Files and symbols

### `__init__.py`

Package marker with the service docstring; it defines no code symbols.

### `main.py`

Builds the FastAPI application, conditionally installs CORS middleware, mounts the versioned API router, and defines service-wide utility endpoints and error handling.

- `custom_generate_unique_id(route)`: Produces OpenAPI operation IDs from the route's first tag and function name.
- `app`: Configured `FastAPI` ASGI application; uses `settings.PROJECT_NAME`, serves OpenAPI below `settings.API_V1_STR`, conditionally installs `CORSMiddleware` from `settings.all_cors_origins`, and includes `api_router` at the API prefix.
- `health()`: Handles `GET /health` and returns the service status object.
- `unhandled_exception_handler(request, exc)`: Catch-all async exception handler returning HTTP 500 JSON with the request path; includes `repr(exc)` in the detail only in the local environment.

### `models.py`

Defines request schemas, public response schemas, enums, and the three related SQLModel tables.

- `PreviewRequest`: Pydantic webhook-preview request with the `callback_url` field typed as `HttpUrl`.
- `UserRole`: String enum with `member` and `staff` values.
- `UserBase`: Shared user fields `email` (unique, indexed, max 255) and `role` (defaults to `UserRole.member`, max 50).
- `User`: `user` table model adding UUID `id`, `hashed_password`, and the cascading `records` relationship to `Record`.
- `UserCreate`: User creation schema adding an 8–128 character plaintext `password` to `UserBase` fields.
- `UserPublic`: Public user schema adding required UUID `id` to `UserBase` fields.
- `UsersPublic`: Paginated user collection with `data` (`list[UserPublic]`) and `count`.
- `RecordType`: String enum whose current value is `lab_result`.
- `RecordStatus`: String enum whose current value is `released`.
- `RecordBase`: Shared record fields `type`, optional `summary` (max 255), and `status`.
- `RecordCreate`: Record creation schema; adds no fields beyond `RecordBase`.
- `Record`: `record` table model. `__table_args__` enforces unique `(user_id, summary)` values; fields and relationships are UUID `id`, cascading foreign-key `user_id`, optional `user`, and cascading `notes`.
- `RecordPublic`: Public record schema adding UUID `id` and `user_id` to `RecordBase` fields.
- `RecordsPublic`: Paginated record collection with `data` (`list[RecordPublic]`) and `count`.
- `RecordNoteBase`: Shared record-note field `note` (max 255).
- `RecordNoteCreate`: Record-note creation schema; adds no fields beyond `RecordNoteBase`.
- `RecordNote`: `recordnote` table model. `__table_args__` enforces unique `(record_id, note)` values; fields and relationships are UUID `id`, cascading foreign-key `record_id`, and optional `record`.
- `RecordNotePublic`: Public note schema adding UUID `id` and `record_id` to `RecordNoteBase` fields.
- `RecordNotesPublic`: Notes-for-record response with `record_id`, `data` (`list[RecordNotePublic]`), and `count`.
- `Message`: Generic response schema with `message`.
- `Token`: OAuth2 token response with `access_token`, `token_type` (default `bearer`), and `expires_in` seconds.
- `TokenPayload`: Decoded JWT claims model with optional `sub`.

### `crud.py`

Provides transactional SQLModel create and lookup operations used by authentication, routes, seed data, and tests.

- `create_user(session=, user_create=)`: Hashes the submitted password, inserts a `User`, commits, refreshes, and returns it.
- `get_user_by_email(session=, email=)`: Returns the first user matching an email, or `None`.
- `authenticate(session=, email=, password=)`: Looks up a user and verifies the supplied password; returns the user on success and `None` otherwise.
- `create_record(session=, record_in=, owner_id=)`: Inserts a `Record` bound to the owner UUID, commits, refreshes, and returns it.
- `create_record_note(session=, record_note_in=, record_id=)`: Inserts a `RecordNote` bound to the record UUID, commits, refreshes, and returns it.

### `backend_pre_start.py`

Executable production-startup database readiness probe with Tenacity retries.

- `logger`: Module logger after INFO-level logging configuration.
- `max_tries`: Retry limit of 300 attempts.
- `wait_seconds`: Fixed one-second delay between attempts.
- `init(db_engine)`: Opens a session and executes `SELECT 1`; logs and re-raises failures so Tenacity retries them.
- `main()`: Logs lifecycle messages and probes the shared database `engine`.

### `tests_pre_start.py`

Executable test-startup database readiness probe. It intentionally mirrors the backend probe so test orchestration can wait on its configured database.

- `logger`: Module logger after INFO-level logging configuration.
- `max_tries`: Retry limit of 300 attempts.
- `wait_seconds`: Fixed one-second delay between attempts.
- `init(db_engine)`: Opens a session and executes `SELECT 1`; logs and re-raises failures so Tenacity retries them.
- `main()`: Logs lifecycle messages and probes the shared database `engine`.

### `initial_data.py`

Executable database seeding entry point.

- `logger`: Module logger after INFO-level logging configuration.
- `init()`: Opens a session on the shared `engine` and delegates to `core.db.init_db`.
- `main()`: Logs lifecycle messages around `init()`.
