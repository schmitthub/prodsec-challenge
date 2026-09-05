# HTTP endpoint declarations

Every module declares PolicyRouter(protected_policy=...). Handlers consume named
bindings with Annotated[T, FromPolicy(Policy.binding)]. Raw dependencies, database
or service imports, and direct provider calls belong in api/policies.
Provider results keep their actual Python types; response_model independently
defines public serialization, including conversion of table objects to schemas.

- records.py: owner-scoped reads; notes explicitly override to OwnerOrStaffNotesPolicy.
- search.py: separate HTTP module using the same RecordPolicy.
- users.py: /me, bound to UserPolicy.
- login.py: public OAuth2 credential exchange through LoginPolicy.
- health.py: public unversioned liveness; app/main.py mounts it separately.
- webhooks.py: staff-only VendorPreviewPolicy operation.

Public router applications and use_policy overrides require rule-specific
nosemgrep comments with preceding justifications; the gate audits and prints them.

## Direct files and symbols

- `__init__.py`: package marker/public re-exports.
- `health.py`: `router`; `health()`.
- `login.py`: `router`; `login_access_token()`.
- `records.py`: `router`; `list_my_records()`; `read_record()`; `read_record_notes()`.
- `search.py`: `router`; `search_records()`.
- `users.py`: `router`; `read_me()`.
- `webhooks.py`: `router`; `preview_vendor_webhook()`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
