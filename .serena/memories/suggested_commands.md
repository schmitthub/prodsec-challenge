# Commands

```bash
uv sync                                        # always first in container (.venv is tmpfs, empty each start)
uv run python -m unittest discover -s tests
uv run python -m unittest tests.test_records.RecordsApiTests.test_health_check
uv run uvicorn app.main:app --reload           # :8000, /docs
docker build -t records-api . && docker run --rm -p 8000:8000 records-api

uv run ruff check --fix . && uv run ruff format .
prek run --all-files                           # all hooks: ruff, gitleaks, bandit, semgrep (python + actions), osv-scanner
prek run <hook-id> --all-files                 # single hook (semgrep, bandit, gitleaks, osv-scanner)
```

Scanners are NOT uv deps — prek installs each from its pinned `rev` into its own cache. `uv run semgrep|bandit|osv-scanner` do not exist.

Auth for manual API testing: `POST /api/login` `{"email","password"}` → bearer. Accounts: alice/bob (`member`), clinician (`staff`); password = `<name>-password`.

GitHub from container: `gh issue`/`gh pr` (GraphQL) blocked by firewall; use REST `gh api repos/schmitthub/<repo>/...`.
