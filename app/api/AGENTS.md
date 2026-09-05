# API composition and authentication

- deps.py owns session lifecycle, OAuth bearer parsing, JWT decoding, and current
  user lookup. It contains no business authorization vocabulary.
- main.py composes login, users, records, search, and webhook routers. Health is
  mounted separately by app/main.py to preserve its unversioned path.
- policies/ owns reviewed application authorization providers and named policies.
- routes/ owns thin HTTP declarations consuming FromPolicy bindings.

All HTTP operations are discovered and structurally checked from the mounted app.
There is no generated endpoint manifest. The closest child guide owns its symbols.

## Direct files and symbols

- `__init__.py`: package marker/public re-exports.
- `deps.py`: `reusable_oauth2`; `get_db()`; `SessionDep`; `TokenDep`; `decode_oauth2_token()`; `get_current_user()`; `CurrentUser`.
- `main.py`: `api_router`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
