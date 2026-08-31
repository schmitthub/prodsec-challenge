# Task completion checklist

Run before declaring a task done:

```bash
uv run ruff check --fix . && uv run ruff format .
uv run python -m unittest discover -s tests
prek run --all-files          # bandit, semgrep (python + actions), osv, gitleaks, ruff, yaml/whitespace
```

- Touched `requirements.txt` or `pyproject.toml` deps → update the other + `uv lock`.
- Touched `.github/workflows/*` → `uv run semgrep scan --config p/github-actions --config .semgrep/ --error`; keep SHA pins + version comments.
- Bumped semgrep → update both `security.yml` digest and `.pre-commit-config.yaml` comment.
- Update `challenge/notes.md` status when a deliverable moves.
- Commit via normal `git commit` so hooks run (bypass flags are blocked by a Claude hook).
