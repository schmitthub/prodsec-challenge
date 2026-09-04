# Conventions

## App code
- Protected route signature: `current_user: Annotated[User, Depends(get_current_user)]`; authz (owner/role) done inline per route, 404 (not 403) on foreign resource in `/notes`.
- Routers: `APIRouter(prefix="/api", tags=[...])`, one module per resource under `../../app/api/routes/`, registered in `../../app/main.py`.
- Modern typing (`X | None`, `dict[str, Any]`), `from __future__ import annotations` where needed. Ruff formats/lints; no docstrings expected.
- Tests: `unittest.TestCase`, module-level `login()`/`auth_headers()` helpers, module-level `TestClient(app)`.

## CI / workflows
- Actions SHA-pinned + `# vX.Y.Z` comment. Dependabot groups actions/pip/docker weekly with `chore(deps):` prefix.
- Reusable workflows (`security.yml`, `test.yml`, `build.yml`) take permissions from the calling job; declare per-job in callers.
- Release attestation identity anchored to `.github/workflows/build.yml` (SLSA L3 style); don't move build/sign steps into `release.yml`.
- Scanner exclusions: `.semgrepignore`, `.gitleaksignore`, gitleaks baseline `gitleaks-report.json` (not yet created).

## Agent documentation
- Every real directory under `../../app/`, `../../config/`, `../../helpers/`, `scripts/`, and `../../tests/` has a localized `AGENTS.md`; its sibling `CLAUDE.md` is a portable relative symlink to `AGENTS.md`.
- Keep each guide's direct-file symbol map synchronized when code files or symbols change. Parent guides summarize child directories; each child guide owns its direct files.
- `.github/instructions/python-security.instructions.md` adds all-Python Copilot review priorities for access control, injection, SSRF, JWTs, disclosure, security logging, and feature-relevant invariant tests; it supplements general review.
