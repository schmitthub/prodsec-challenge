# Reviewed application policies

This directory is the trusted business authorization layer, protected by CODEOWNERS.
Use normal Python/FastAPI/SQLModel here; scanners enforce its boundary, not the
correctness of arbitrary predicates. Protect called helpers under CODEOWNERS too.

- base.py defines AuthenticatedPolicy using the real current-user dependency.
  Every principal declaration uses ClassVar[Principal], preserving the mutable
  attribute contract for both authenticated and PUBLIC policies.
- records.py owns owner-filtered single/list/search queries and the explicit
  owner-or-staff composite notes provider. RecordPolicy and OwnerOrStaffNotesPolicy
  deliberately expose different bindings. Missing and foreign records both 404.
  Resource symbols name RecordBase/RecordNoteBase families. TypedDict results keep
  authorized table objects; route response_model declarations own public schemas.
- users.py exposes only the current User under UserPolicy.
- login.py owns the anonymous OAuth credential exchange and no-store headers.
- health.py declares anonymous liveness. PUBLIC uses need reviewed suppressions.
- webhooks.py owns the staff check, URL allowlist, redirect prohibition, timeout,
  and bounded preview. VendorPreview is a service resource, not a database row.

Policy names are application-owned symbols; the reusable core knows no roles,
resource types, owner keys, or authentication scheme. New behavior needs policy
unit/integration tests and corresponding rule fixtures for new exception symbols.

## Direct files and symbols

- `__init__.py`: package marker/public re-exports.
- `base.py`: `AuthenticatedPolicy (principal)`.
- `health.py`: `health_status()`; `HealthPolicy (principal, status)`.
- `login.py`: `NO_STORE_HEADERS`; `login_access_token()`; `LoginPolicy (principal, methods, credentials)`.
- `records.py`: `RecordPage (data, count)`; `RecordNotes (record_id, data, count)`; `record_reader()`; `owned_record()`; `_page()`; `owned_records()`; `search_owned_records()`; `owner_or_staff_notes()`; `RecordPolicy (principal, record, page, search)`; `OwnerOrStaffNotesPolicy (principal, notes)`.
- `users.py`: `current_user()`; `UserPolicy (me)`.
- `webhooks.py`: `FETCH_TIMEOUT_SECONDS`; `DisallowedUrlError`; `_check_allowed()`; `_fetch_allowed()`; `preview_vendor_webhook()`; `VendorPreviewPolicy (methods, preview)`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
