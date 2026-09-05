# Conventions

## App code
- FastAPI app mounts `app.api.main.api_router` at `settings.API_V1_STR`; route modules live in `app/api/routes/`.
- `app/api/deps.py` owns authentication/session primitives. Reviewed `app/api/policies/` providers own authorization and data access; route handlers consume `FromPolicy(Policy.binding)` under mandatory `PolicyRouter(protected_policy=...)`. Generic machinery lives in `app/authz/`; see `mem:design/access-control-deps`.
- PUBLIC and policy overrides require blocking scanner diagnostics plus justified rule-specific suppressions. The existing gate always scans app/ contracts and prints accepted exceptions. Mounted-route discovery replaces endpoint manifests.
- Asset declarations, provider return types, and HTTP response schemas are separate contracts. Use shared base/domain marker symbols for asset families; do not infer authorization from sibling classes or compare assets with response types. Record providers return RecordPage/RecordNotes TypedDict results; FastAPI response_model performs public projection.
- Owner-scoped endpoints filter/query by `current_user.id`; foreign and missing records both return 404. Staff access is explicit per route.
- SQLModel tables and public/input schemas live in `app/models.py`; CRUD writes call `session.add/commit/refresh`; migrations own schema creation.
- Search uses SQLModel expressions and escaped case-insensitive containment; webhook fetches require exact case-insensitive allowlist membership, HTTPS, timeout, and redirects disabled.
- User selected mypy + Ruff for project linting; do not substitute another type checker. `scripts/lint.sh` is the shared checking-only pre-commit/CI entry point, using `uv run --frozen` and uv.lock pins. Mypy checks app/ including the live Alembic runner; historical generated revisions are excluded. Ruff checks app/, scripts/, tests/, .github/scripts/, and .semgrep/.
- Mypy strict is supplemented by mutable-override, explicit-override, coded ignores, no unimported Any, unreachable/redundant/possibly-undefined expressions, and unused awaitables. Strict alone did not catch the principal override. Every policy principal must retain ClassVar[Principal], where Principal is exported by app.authz.
- Ruff requires complete signatures, rejects Any function annotations, broad/stale ignores/noqa, mutable defaults, blind catches, invalid mock assertions, unsafe async patterns, and other correctness mistakes. Two documented ANN401 exceptions preserve FastAPI's heterogeneous keyword forwarding; scanner fixtures have scoped exemptions. Requests stubs are a dev dependency so no import-untyped suppression is needed.

## Tests
- Pytest fixtures in `tests/conftest.py`; tests use the real Postgres engine and clean tables after the session.
- API tests use FastAPI `TestClient`; outbound requests are monkeypatched.
- Factories live in `tests/utils/`; API tests in `tests/api/`; CRUD tests in `tests/crud/`; startup-probe tests in `tests/scripts/`.
- Keep `tests/api/test_authz_invariant.py` schema-driven and aligned with authenticated GET operations under the versioned API prefix; it probes foreign user/record IDs and keeps `EXEMPT_ROUTES` normally empty.

## CI / workflows
- Actions are SHA-pinned with `# vX.Y.Z` comments. Reusable callers grant permissions per job.
- Scanner gates: Semgrep general rules gate new top-severity PR findings; authorization contracts scan all app/ and block locally and on both PR/main, with visible justified exceptions. Bandit new HIGH; Gitleaks baseline-aware; dependency review High+; container OSV advisory/best-effort.
- Scanner versions must match between `security.yml` or the local composite and `.pre-commit-config.yaml`.
- `.semgrep/fastapi-access-control.py` is deliberately invalid, line-sensitive scanner input. Preserve its targeted Ruff noqa codes and fmt-off header: removing/reordering imports or moving ruleid/ok comments destroys test cases. The Semgrep fixture gate still checks every expected finding.
- `uv.lock` is the SCA/SBOM dependency input; scanners stay out of the uv dependency groups.

## Agent documentation
- Every source-bearing directory under `app/`, `scripts/`, and `tests/` owns `AGENTS.md`; sibling `CLAUDE.md` is the relative symlink `AGENTS.md`.
- Each guide documents directory role, every direct code file, and every direct-file symbol, including module globals and dependency/type aliases. Parent guides summarize child directories; child guides own their direct files.
- Exclude generated cache directories. Keep inventories and symlinks synchronized with file/symbol moves.
