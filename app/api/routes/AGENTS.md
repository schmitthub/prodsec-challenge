# `app/api/routes/`

## Directory summary

FastAPI endpoint modules for login, identity and record reads, record search, and staff-only vendor webhook previews. Every route module exports a `PolicyRouter`; `app.api.main` includes all four routers beneath the configured versioned API prefix.

## Role in the project

These modules are the HTTP boundary. They declare access with the vocabulary in `app.api.deps` (`CurrentUser`, `Owned[Model]`, `AnyOwner[Model]`, `OwnedQuery[Model]`, `require(...)`, `PUBLIC`) and never query: no route takes a `Session` except the `PUBLIC` login route, and `PolicyRouter` rejects anything else at import. Schemas and tables come from `app.models`, persistence and security helpers from `app.crud` and `app.core`. Authentication and loader mechanics live in the parent `api/` guide.

## Files and symbols

### `__init__.py`

Package marker with the route-package docstring; it defines no code symbols.

### `login.py`

Implements the OAuth2 resource-owner password grant using form-encoded credentials.

- `router`: `PolicyRouter` tagged `auth`; registers `POST /login` with `dependencies=[PUBLIC]`, the only unauthenticated route and the only one that may take `SessionDep`.
- `NO_STORE_HEADERS`: `Cache-Control: no-store` and `Pragma: no-cache` headers applied to successful and rejected token responses.
- `login_access_token(session, response, form_data)`: Handles `POST /login`. It authenticates `form_data.username` as the account email and `form_data.password`. Invalid credentials return RFC-style HTTP 400 `invalid_grant` JSON with the no-cache headers; success returns a signed `Token` with `expires_in` derived from `settings.ACCESS_TOKEN_EXPIRE_MINUTES` and updates the response with the same headers.

### `records.py`

Implements authenticated identity, record-list, individual-record, and record-note reads.

- `router`: `PolicyRouter` tagged `records`.
- `read_me(current_user)`: Handles `GET /me` and returns the authenticated user as `UserPublic`.
- `list_my_records(records, skip=0, limit=100)`: Handles `GET /records`; `records` is `OwnedQuery[Record]`, already filtered to the caller, so the route only pages and counts it into `RecordsPublic`.
- `read_record(record)`: Handles `GET /records/{record_id}`; `record` is `Owned[Record]`, so foreign and missing records are both 404 before the body runs. Returns `RecordPublic`.
- `read_record_notes(record)`: Handles `GET /records/{record_id}/notes`; `record` is `AnyOwner[Record]`: the owner always passes, staff pass via `records:read:any`, anyone else gets 404. Returns `RecordNotesPublic`.

### `search.py`

Implements caller-scoped record summary search.

- `router`: `PolicyRouter` tagged `search`.
- `search_records(q, records, skip=0, limit=100)`: Handles `GET /search`. `q` is constrained to 1–255 characters; `records` is `OwnedQuery[Record]`, narrowed with a case-insensitive, auto-escaped substring match on `summary`, then paged and counted into `RecordsPublic`.

### `webhooks.py`

Implements a staff-only outbound preview with HTTPS host allowlisting, disabled redirects, and a bounded response preview.

- `router`: `PolicyRouter` tagged `webhooks`; the preview route declares `dependencies=[require(Scope.webhooks_preview)]`, a scope only staff hold, so members receive 403 and anonymous callers 401.
- `FETCH_TIMEOUT_SECONDS`: Outbound request timeout, currently two seconds.
- `DisallowedUrlError`: Internal `ValueError` subclass raised when a URL's scheme or host violates the configured policy.
- `_check_allowed(url)`: Requires HTTPS and an exact, case-insensitive host match in `settings.webhook_allowed_hosts`.
- `_fetch_allowed(url)`: Validates the URL, then performs `requests.get` with the fixed timeout and redirects disabled.
- `preview_vendor_webhook(request)`: Handles `POST /webhooks/vendor-preview`. Disallowed URLs produce HTTP 400; outbound request failures retain the route's default HTTP 200 response while placing `status_code: 500`, a null content type, and the exception text in the response body. Successful fetches return the upstream status, content type, and first 200 response-text characters.

## Local guide aliases

- `AGENTS.md`: This directory-scoped contributor guide.
- `CLAUDE.md`: Portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
