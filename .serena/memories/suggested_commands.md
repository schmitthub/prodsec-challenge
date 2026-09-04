# Commands

```bash
uv sync --frozen
docker compose up -d db
uv run bash scripts/prestart.sh                 # DB wait, Alembic upgrade, local seed
uv run pytest tests
uv run pytest tests/api/routes/test_records.py
uv run fastapi dev app/main.py                  # :8000, docs at /docs
docker compose up --build

uv run bash scripts/lint.sh                     # strict mypy + Ruff check/format check on app
uv run bash scripts/format.sh                   # Ruff fix/format app + scripts
prek run --all-files                            # fixers, scanners, compose-backed pytest
prek run semgrep --all-files
scripts/sarif-scan.sh                           # full local SARIF, no gates/baselines
```

Tests use real Postgres. The hook's pytest entry builds/runs the compose backend and mounts `app/`, `tests/`, and `scripts/`.

Scanners are prek-managed, not uv dependencies. `uv run semgrep|bandit|osv-scanner` is not the supported path.

Local fixture users: Alice/Bob members and clinician staff; shared password is `SEED_PASSWORD`. Login uses form-encoded OAuth2 fields `username=<email>` and `password=<value>` at `POST /api/v1/login`.
