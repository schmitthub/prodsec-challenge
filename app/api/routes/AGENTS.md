# `app/api/routes/`

## Directory summary

FastAPI endpoint modules for login, identity and record reads, record search, and staff-only vendor webhook previews. Every route module exports an `APIRouter`; `app.api.main` includes all four routers beneath the configured versioned API prefix.

## Role in the project

These modules are the HTTP boundary. They use dependencies from `app.api.deps`, schemas and tables from `app.models`, persistence and security helpers from `app.crud` and `app.core`, and return response models declared on each route. Authentication and database-session mechanics remain in the parent `api/` guide.

## Files and symbols

### `__init__.py`

Package marker with the route-package docstring; it defines no code symbols.

### `login.py`

Implements the OAuth2 resource-owner password grant using form-encoded credentials.

- `router`: `APIRouter` tagged `auth`; registers `POST /login`.
- `NO_STORE_HEADERS`: `Cache-Control: no-store` and `Pragma: no-cache` headers applied to successful and rejected token responses.
- `login_access_token(session, response, form_data)`: Handles `POST /login`. It authenticates `form_data.username` as the account email and `form_data.password`. Invalid credentials return RFC-style HTTP 400 `invalid_grant` JSON with the no-cache headers; success returns a signed `Token` with `expires_in` derived from `settings.ACCESS_TOKEN_EXPIRE_MINUTES` and updates the response with the same headers.

### `records.py`

Implements authenticated identity, record-list, individual-record, and record-note reads.

- `router`: `APIRouter` tagged `records`.
- `read_me(current_user)`: Handles `GET /me` and returns the authenticated user as `UserPublic`.
- `list_my_records(session, current_user, skip=0, limit=100)`: Handles `GET /records`; counts and pages records whose `user_id` matches the caller, returning `RecordsPublic`.
- `read_record(session, current_user, record_id)`: Handles `GET /records/{record_id}`; returns the caller-owned record as `RecordPublic`, using the same 404 response for missing and foreign records.
- `read_record_notes(session, current_user, record_id)`: Handles `GET /records/{record_id}/notes`; permits the owner or any staff user and returns `RecordNotesPublic`, while missing and unauthorized records both produce 404.

### `search.py`

Implements caller-scoped record summary search.

- `router`: `APIRouter` tagged `search`.
- `search_records(q, current_user, session, skip=0, limit=100)`: Handles `GET /search`. `q` is constrained to 1–255 characters; the query counts and pages only the caller's records using case-insensitive, auto-escaped substring matching, then returns `RecordsPublic`.

### `webhooks.py`

Implements a staff-only outbound preview with HTTPS host allowlisting, disabled redirects, and a bounded response preview.

- `router`: `APIRouter` tagged `webhooks`; registers the preview route with `get_current_staff_user` as a router dependency.
- `FETCH_TIMEOUT_SECONDS`: Outbound request timeout, currently two seconds.
- `DisallowedUrlError`: Internal `ValueError` subclass raised when a URL's scheme or host violates the configured policy.
- `_check_allowed(url)`: Requires HTTPS and an exact, case-insensitive host match in `settings.webhook_allowed_hosts`.
- `_fetch_allowed(url)`: Validates the URL, then performs `requests.get` with the fixed timeout and redirects disabled.
- `preview_vendor_webhook(request)`: Handles `POST /webhooks/vendor-preview`. Disallowed URLs produce HTTP 400; outbound request failures retain the route's default HTTP 200 response while placing `status_code: 500`, a null content type, and the exception text in the response body. Successful fetches return the upstream status, content type, and first 200 response-text characters.

## Local guide aliases

- `AGENTS.md`: This directory-scoped contributor guide.
- `CLAUDE.md`: Portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
