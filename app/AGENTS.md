# ``

## Directory summary

This Python package implements the FastAPI records service. It owns application startup, bearer-token authentication, request/response models, and the in-memory data access layer. The `routes` subpackage contains the HTTP endpoint modules and has its own localized guide.

## Module role

`app` is the service's runtime package: `main.py` assembles the ASGI application, while `core/auth.py`, `core/db.py`, and `models.py` provide shared dependencies used by the route modules.

## Code files and symbols

- `__init__.py` — marks the directory as a package and describes the records API; it defines no code symbols.
- `main.py` — constructs and configures the FastAPI entry point. `app` is the ASGI application and router registry; `health` serves the health check; `unhandled_exception_handler` converts otherwise-unhandled exceptions into JSON responses.
- `core/auth.py` — issues and validates bearer tokens and resolves authenticated users. `JWT_SECRET`, `JWT_ALGORITHM`, and `ACCESS_TOKEN_MINUTES` configure token handling; `oauth2_scheme` extracts bearer credentials; `create_access_token` builds a user token; `decode_access_token` decodes it or raises an authentication error; `get_current_user` loads its subject as a `User` dependency.
- `core/db.py` — provides the service's in-memory users and records plus query helpers. `USERS` and `RECORDS` are the backing datasets; `get_user_by_email`, `get_user_by_id`, and `get_record` perform individual lookups; `list_records_for_user` filters records by owner; `search_records` loads records into an in-memory SQLite table and searches released summaries.
- `models.py` — defines shared Pydantic API models. `User` represents the authenticated identity (`id`, `email`, `role`); `TokenResponse` represents the login response (`access_token`, `token_type`).
