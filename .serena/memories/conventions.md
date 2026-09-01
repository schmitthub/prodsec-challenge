# Conventions

## App code
- Protected route signature: `current_user: Annotated[User, Depends(get_current_user)]`; authz (owner/role) done inline per route, 404 (not 403) on foreign resource in `/notes`.
- Routers: `APIRouter(prefix="/api", tags=[...])`, one module per resource under `app/routes/`, registered in `app/main.py`.
- Modern typing (`X | None`, `dict[str, Any]`), `from __future__ import annotations` where needed. Ruff formats/lints; no docstrings expected.
- Tests: `unittest.TestCase`, module-level `login()`/`auth_headers()` helpers, module-level `TestClient(app)`.

## CI / workflows
- Actions SHA-pinned + `# vX.Y.Z` comment. Dependabot groups actions/pip/docker weekly with `chore(deps):` prefix.
- Reusable workflows (`security.yml`, `test.yml`, `build.yml`) take permissions from the calling job; declare per-job in callers.
- Custom semgrep rules live in `.semgrep/*.yaml`; each must run in both CI and the matching pre-commit hook.
- Release attestation identity anchored to `.github/workflows/build.yml` (SLSA L3 style); don't move build/sign steps into `release.yml`.
- Scanner exclusions: `.semgrepignore`, `.gitleaksignore`, gitleaks baseline `gitleaks-report.json` (not yet created).
