# Task completion checklist

Use checks proportional to changed files; do not run fix-capable whole-tree commands for docs-only work.

## Application/test changes
```bash
uv sync --frozen
docker compose up -d db
uv run bash scripts/prestart.sh
uv run pytest tests
uv run bash scripts/lint.sh
```

## Repository gates
```bash
prek run --all-files
```
This may apply Ruff/whitespace fixes and runs compose-backed pytest when app/test Python is in scope; inspect all resulting edits.

## Documentation-only changes
- `git diff --check`.
- Validate documented files/symbols against the current source.
- For directory guides, verify every source-bearing directory has `AGENTS.md` and resolving relative `CLAUDE.md -> AGENTS.md`.

## Conditional checks
- Dependency edits: update `pyproject.toml` and `uv.lock`; scanners remain outside uv deps.
- Workflow edits: run the Semgrep/actions hook; retain action SHA pins/comments and least permissions.
- Authorization contract/rule edits: run `uv run python .github/scripts/semgrep_gate.py --contracts` with pinned Semgrep on PATH (fixtures, full app/ scan, visible suppression audit). Include positive and negative fixtures; changing provider/response types must not imply a policy change. Run tests/scanners without the DB when modifying the gate itself.
- Scanner bumps: update CI/composite and matching pre-commit pin together.
- Accepted secret baseline changes: regenerate redacted `gitleaks-report.json`; do not use ignore entries as a substitute.
- Schema changes: add/test an Alembic migration and prove upgrade behavior.
- Commit normally so repository hooks execute; never bypass them.
