# Task completion checklist

Run before declaring a task done:

```bash
uv run ruff check --fix . && uv run ruff format .
uv run python -m unittest discover -s tests
prek run --all-files          # gitleaks (baseline gitleaks-report.json), bandit, semgrep python+actions, osv-scanner, ruff, yaml/whitespace
```

- Touched `requirements.txt` or `pyproject.toml` deps → update the other + `uv lock`. Do not add scanners to the uv dev group.
- Touched `.github/workflows/*` → `prek run semgrep --all-files` covers the actions hook; keep SHA pins + version comments.
- Bumped a scanner in CI (`security.yml` semgrep image tag / `GITLEAKS_VERSION`) → bump the matching hook `rev` in `.pre-commit-config.yaml` (dependabot won't).
- New accepted secret finding → regenerate `gitleaks-report.json` (`gitleaks git . --report-path gitleaks-report.json`), not `.gitleaksignore`.
- Update `challenge/notes.md` status when a deliverable moves.
- Commit via normal `git commit` so hooks run (bypass flags are blocked by a Claude hook). Claude commits its own work separately with the co-author trailer.
