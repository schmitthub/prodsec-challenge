# Commands

```bash
uv sync                                        # always first in container (.venv is tmpfs, empty each start)
uv run python -m unittest discover -s tests
uv run python -m unittest tests.test_records.RecordsApiTests.test_health_check
uv run uvicorn app.main:app --reload           # :8000, /docs
docker build -t records-api . && docker run --rm -p 8000:8000 records-api

uv run ruff check --fix . && uv run ruff format .
uv run bandit -r app/ -c pyproject.toml
uv run semgrep scan --config p/python --config p/security-audit --config .semgrep/ --config p/owasp-top-ten --error
uv run semgrep scan --config p/github-actions --config .semgrep/ --error   # workflows only
uv run osv-scanner scan source .
prek run --all-files                           # all pre-commit hooks
```

Auth for manual API testing: `POST /api/login` `{"email","password"}` → bearer. Accounts: alice/bob (`member`), clinician (`staff`); password = `<name>-password`.

GitHub from container: `gh issue`/`gh pr` (GraphQL) blocked by firewall; use REST `gh api repos/schmitthub/<repo>/...`.
