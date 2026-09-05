# Reusable authorization contracts

Application-independent code: never import app.api, application models, settings,
SQLModel, or a database driver. Providers are trusted application implementations;
this package validates symbolic declarations and actual dependency wiring.

- contracts.py owns Policy, named resource Binding declarations, FromPolicy, PUBLIC,
  and explicit use_policy overrides. Bindings carry resource types and a provider.
  Resources may be shared bases or domain markers, independent of result/schema
  types. The framework never infers authorization from class inheritance.
- router.py owns mandatory router policies, binding membership, method checks, and
  per-registration metadata; it does not rewrite endpoint functions.
- discovery.py isolates FastAPI 0.141 lazy-include internals and validates mounted
  dependencies, hidden routes, and coverage. Unsupported mounts/websockets fail.
- __init__.py exposes the public package API.

Verification: uv run pytest --confcutdir=tests/authz tests/authz.

## Direct files and symbols

- `__init__.py`: `__all__`.
- `contracts.py`: `T`; `PolicyError`; `Public`; `PUBLIC`; `Binding (__post_init__, resources, provider)`; `Policy (bindings, validate, principal, methods)`; `FromPolicy (__init__, binding)`; `_PolicyOverride (__init__, policy)`; `use_policy()`.
- `discovery.py`: `MountedContract (policy, public, overridden, resources, method, path, contract)`; `_walk()`; `_calls()`; `discover_contracts()`.
- `router.py`: `RouteContract (policy, bindings, overridden)`; `PolicyRouter (__init__, _validate_policy, add_api_route)`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
