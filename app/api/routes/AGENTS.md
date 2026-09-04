# ``

## Directory summary

This Python subpackage contains the FastAPI routers for authentication, record access, search, and webhook preview operations. Each route module exports an `APIRouter` that `..main.py` mounts into the service.

## Module role

`app.routes` is the HTTP boundary of the application. Its handlers validate request models, apply authentication or role/ownership checks where implemented, call shared `app.auth` and `app.db` helpers, and shape API responses.

## Code files and symbols

- `__init__.py` — marks the directory as the route package and documents its purpose; it defines no code symbols.
- `login.py` — OAuth2 password-grant token endpoint (RFC 6749 §4.3). `router` registers `POST /login`; `login_access_token` takes `OAuth2PasswordRequestForm` (form-encoded, `username` is the email), returns `Token` (`access_token`, `token_type`, `expires_in`) with `Cache-Control: no-store`, and answers bad credentials with 400 `{"error": "invalid_grant"}`. JSON bodies are rejected with 422.
- `records.py` — implements authenticated identity and record endpoints. `router` registers the records routes; `read_me` returns the current user; `list_my_records` returns records owned by that user; `read_record` looks up one record; `read_record_notes` returns notes after staff-or-owner authorization.
- `search.py` — exposes authenticated record search. `router` registers the search route; `search_records` passes query parameter `q` to `app.db.search_records` and returns its results.
- `webhooks.py` — implements staff-only vendor webhook previews. `router` registers the webhook route; `PreviewRequest` validates `callback_url`; `preview_vendor_webhook` fetches that URL and returns selected response metadata plus a bounded text preview.
