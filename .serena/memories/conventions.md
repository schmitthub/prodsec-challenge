# Conventions

## App code
- FastAPI app mounts `app.api.main.api_router` at `settings.API_V1_STR`; route modules live in `app/api/routes/`.
- Shared dependencies use aliases from `app/api/deps.py`: `SessionDep`, `CurrentUser`; staff-only routes depend on `get_current_staff_user`.
- Owner-scoped endpoints filter/query by `current_user.id`; foreign and missing records both return 404. Staff access is explicit per route.
- SQLModel tables and public/input schemas live in `app/models.py`; CRUD writes call `session.add/commit/refresh`; migrations own schema creation.
- Search uses SQLModel expressions and escaped case-insensitive containment; webhook fetches require exact case-insensitive allowlist membership, HTTPS, timeout, and redirects disabled.
- Modern typing (`X | None`, `dict[str, Any]`); Ruff format/lint and strict mypy apply to `app/`.

## Tests
- Pytest fixtures in `tests/conftest.py`; tests use the real Postgres engine and clean tables after the session.
- API tests use FastAPI `TestClient`; outbound requests are monkeypatched.
- Factories live in `tests/utils/`; API tests in `tests/api/`; CRUD tests in `tests/crud/`; startup-probe tests in `tests/scripts/`.
- Keep `tests/api/test_authz_invariant.py` schema-driven and aligned with authenticated GET operations under the versioned API prefix; it probes foreign user/record IDs and keeps `EXEMPT_ROUTES` normally empty.

## CI / workflows
- Actions are SHA-pinned with `# vX.Y.Z` comments. Reusable callers grant permissions per job.
- Scanner gates: Semgrep new top severity; Bandit new HIGH; Gitleaks baseline-aware; dependency review High+; container OSV advisory/best-effort.
- Scanner versions must match between `security.yml` or the local composite and `.pre-commit-config.yaml`.
- `uv.lock` is the SCA/SBOM dependency input; scanners stay out of the uv dependency groups.

## Agent documentation
- Every source-bearing directory under `app/`, `scripts/`, and `tests/` owns `AGENTS.md`; sibling `CLAUDE.md` is the relative symlink `AGENTS.md`.
- Each guide documents directory role, every direct code file, and every direct-file symbol, including module globals and dependency/type aliases. Parent guides summarize child directories; child guides own their direct files.
- Exclude generated cache directories. Keep inventories and symlinks synchronized with file/symbol moves.
