# `app/routes/`

## Directory summary

This Python subpackage contains the FastAPI routers for authentication, record access, search, and webhook preview operations. Each route module exports an `APIRouter` that `app/main.py` mounts into the service.

## Module role

`app.routes` is the HTTP boundary of the application. Its handlers validate request models, apply authentication or role/ownership checks where implemented, call shared `app.auth` and `app.db` helpers, and shape API responses.

## Code files and symbols

- `__init__.py` — marks the directory as the route package and documents its purpose; it defines no code symbols.
- `login.py` — implements token login. `router` registers authentication endpoints; `LoginRequest` models email/password credentials; `login` validates those credentials and returns a `TokenResponse` containing a bearer token.
- `records.py` — implements authenticated identity and record endpoints. `router` registers the records routes; `read_me` returns the current user; `list_my_records` returns records owned by that user; `read_record` looks up one record; `read_record_notes` returns notes after staff-or-owner authorization.
- `search.py` — exposes authenticated record search. `router` registers the search route; `search_records` passes query parameter `q` to `app.db.search_records` and returns its results.
- `webhooks.py` — implements staff-only vendor webhook previews. `router` registers the webhook route; `PreviewRequest` validates `callback_url`; `preview_vendor_webhook` fetches that URL and returns selected response metadata plus a bounded text preview.
