# Cross-route API authorization tests

- test_authz_invariant.py discovers secured GET operations through OpenAPI and
  checks that members never receive foreign user/record identifiers.
- test_contracts.py discovers actual mounted contracts, requires authentication
  on every protected operation, checks resource boundaries and the composite
  notes policy, and proves the staff exception does not widen normal reads/search.
- routes/ owns endpoint-specific behavior and real response assertions.

Use real Postgres fixtures from tests/conftest.py. No endpoint inventory or
policy-derived status oracle substitutes for independent business assertions.

## Direct files and symbols

- `__init__.py`: package marker/public re-exports.
- `test_authz_invariant.py`: `EXEMPT_ROUTES`; `SEEDED_MEMBER_EMAILS`; `identifiers_owned_by()`; `string_values()`; `authenticated_get_routes()`; `test_member_never_receives_another_users_identifiers()`.
- `test_contracts.py`: `test_every_protected_operation_requires_identity()`; `test_live_contracts_reflect_asset_boundaries()`; `test_staff_exception_does_not_widen_other_record_operations()`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
