# Reusable contract tests

These tests use plain resource types and integer keys with no application policy,
model, environment, or database dependency. Run independently with:
uv run pytest --confcutdir=tests/authz tests/authz

They cover policy completeness, identity-before-provider execution, unbound and
foreign bindings, raw dependencies, composite policies, public declarations,
unsupported methods, shared endpoint functions, unused bindings, wiring discovery,
and hidden/nested/uncontracted routes.
The asset-family projection test exercises sibling provider results under one
base symbol while HTTP serialization omits internal fields and requires identity.

## Direct files and symbols

- `__init__.py`: package marker/public re-exports.
- `test_contracts.py`: `Document`; `Comment`; `identity()`; `load_document()`; `load_comments()`; `Documents (principal, document)`; `Discussion (principal, document, comments)`; `PublicDocuments (principal, document)`; `test_router_requires_policy()`; `test_policy_requires_explicit_principal()`; `test_policy_requires_resource_bindings()`; `test_authentication_precedes_provider_and_validation()`; `test_asset_family_allows_sibling_results_with_public_projection()`; `test_unbound_endpoint_fails_registration()`; `test_foreign_binding_fails_registration()`; `test_raw_dependency_cannot_bypass_binding()`; `test_composite_policy_executes_each_binding()`; `test_public_is_explicit_and_discoverable()`; `test_hidden_and_nested_uncontracted_routes_are_rejected()`; `test_read_policy_cannot_silently_authorize_writes()`; `test_endpoint_function_is_not_rewritten()`; `test_unused_bindings_do_not_execute()`; `test_discovery_detects_disconnected_authorization()`; `test_duplicate_overrides_and_raw_decorator_dependencies_are_rejected()`; `test_uncontracted_subapplication_is_not_silently_skipped()`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
