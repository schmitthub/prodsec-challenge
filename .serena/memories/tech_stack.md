# Tech stack

- Python 3.11 (`.python-version`; project supports `>=3.11`).
- FastAPI 0.141+, Pydantic 2.13+, pydantic-settings, SQLModel 0.0.42+, SQLAlchemy via SQLModel, psycopg 3.3+, Alembic 1.19+, Postgres 17.
- Auth/security: PyJWT 2.12 (HS256 + `exp`), bcrypt 5, OAuth2 password form. Outbound HTTP uses requests 2.31; tests also use httpx 0.27.
- `pyproject.toml` + `uv.lock` are dependency truth. Dev group: coverage, mypy, pytest, ruff. `requirements.txt` and `Dockerfile.old` are legacy.
- Tests: pytest + FastAPI TestClient against real Postgres; Coverage.py reporting.
- Container: `python:3.11`, uv copied from `ghcr.io/astral-sh/uv:0.5.11`, lock-based sync, fixed unprivileged uid/gid 10001, `fastapi run --workers 4 app/main.py`.
- Compose: Postgres, prestart migration/seed job, backend, and Adminer with external Traefik wiring.
- Security tooling is prek-managed: Gitleaks 8.30.1, Bandit 1.9.4, Semgrep 1.175.0, OSV-Scanner 2.5.1. Keep CI/composite pins aligned with `.pre-commit-config.yaml`.
- Release tooling: Syft SBOMs, Cosign keyless bundles, GitHub artifact attestations; image ships as a signed docker archive, not through a registry.
