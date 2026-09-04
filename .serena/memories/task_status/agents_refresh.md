# Agent guide refresh status

Complete.

- Refreshed root, `app/`, `scripts/`, and `tests/` guides for the current Postgres/SQLModel/pytest architecture.
- Every one of the 13 source-bearing directories under `app/`, `scripts/`, and `tests/` has a local `AGENTS.md` and exact relative sibling `CLAUDE.md -> AGENTS.md`.
- Every nested code directory received a distinct subagent audit; top-level parent agents reconciled their trees.
- Aggregate validation covered 49 direct code files and 234 AST-defined Python symbols, plus shell and Alembic-template inventories.
- `git diff --check`, final-newline, trailing-whitespace, forbidden-reference, resolving-symlink, and docs/memory-only change checks pass.
- No application, script, or test source changed; test execution was intentionally skipped for documentation-only work.
