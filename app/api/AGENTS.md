# `app/api/`

## Directory summary

Shared FastAPI API wiring. This package owns request-scoped database and authentication dependencies plus the aggregate versioned router; concrete endpoint handlers live in `routes/` and have their own guide.

## Role in the project

`app.main` mounts `main.api_router` under `settings.API_V1_STR`. The router includes every endpoint module. FastAPI resolves the aliases in `deps.py` into a request-scoped session and the authentication chain `CurrentUser` -> `get_current_user` -> `SessionDep` + `TokenDep`; staff-only routes add `get_current_staff_user`.

## Child directories

- `routes/` — login, records, search, and webhook endpoint modules; see `routes/AGENTS.md`.

## Files and symbols

### `__init__.py`

Package marker; it defines no code symbols.

### `main.py`

Composes the endpoint routers exposed by the application.

- `api_router`: Aggregate `APIRouter` that includes, in order, `login.router`, `records.router`, `search.router`, and `webhooks.router`.

### `deps.py`

Defines reusable FastAPI dependency aliases for database sessions, bearer tokens, authenticated users, and staff authorization.

- `reusable_oauth2`: `OAuth2PasswordBearer` configured for the versioned `/login` token URL and the `Bearer` scheme name. `auto_error=False` lets a missing credential reach `decode_oauth2_token` so this module emits the intended 401 response.
- `get_db()`: Generator dependency that opens a SQLModel `Session` on the shared engine, yields it for dependency resolution, and closes it when the request dependency scope exits.
- `SessionDep`: Annotated `Session` dependency backed by `get_db`.
- `TokenDep`: Annotated bearer-token `str` dependency backed by `reusable_oauth2`. At runtime it can receive `None` because the OAuth2 dependency has `auto_error=False`; `decode_oauth2_token` owns that case.
- `RecordDep`: Currently unused annotated bearer-token `str` dependency backed by `reusable_oauth2`; it is equivalent to `TokenDep` and does not perform a record lookup.
- `decode_oauth2_token(token)`: Requires a token, decodes it with `settings.SECRET_KEY` while allowing only `security.ALGORITHM`, and validates the decoded mapping as `TokenPayload`. A missing token raises 401 with `WWW-Authenticate: Bearer`; JWT decoding failures (including expiry) or payload-model validation failures raise 403.
- `get_current_user(session, token)`: Decodes the bearer token, loads `User` by the payload's `sub` primary key, and raises 404 when that user no longer exists.
- `CurrentUser`: Annotated `User` dependency backed by `get_current_user`.
- `get_current_staff_user(current_user)`: Returns the authenticated user only when `role == UserRole.staff`; every other role receives 403.
