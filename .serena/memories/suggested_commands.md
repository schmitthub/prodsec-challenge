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
uv run python .github/scripts/semgrep_gate.py --contracts # contract fixtures, full app scan, suppression audit; requires pinned Semgrep on PATH
uv run pytest --confcutdir=tests/authz tests/authz tests/scanners -q # reusable contracts/gate without Postgres
scripts/sarif-scan.sh                           # full local SARIF, no gates/baselines
```

Application tests use real Postgres; tests/authz and tests/scanners can run independently with --confcutdir above. The hook's pytest entry builds/runs the compose backend and mounts `app/`, `tests/`, `scripts/`, and `.github/` read-only for scanner-gate imports.

Scanners are prek-managed, not uv dependencies. `uv run semgrep|bandit|osv-scanner` is not the supported path.

Local fixture users: Alice/Bob members and clinician staff; shared password is `SEED_PASSWORD`. Login uses form-encoded OAuth2 fields `username=<email>` and `password=<value>` at `POST /api/v1/login`.
