# Clawker container quirks

- `.gitignore` explicitly unignores `/.serena/memories/env/` after the broad env/ENV rules so these notes are tracked. The directory-only exception preserves ignores for `.env` files and actual virtual environments.

- Git may reject the host-mounted checkout with `detected dubious ownership`. For this trusted workspace, use `git -c safe.directory="$PWD" <command>` from the repository root; from subdirectories, use the checkout's exact absolute root. Prefer the per-command exception over global wildcard trust or changing host-mount ownership. Hooks still run. The root AGENTS.md documents this convention.

- Egress firewall is path-scoped (`.clawker.yaml` `security.firewall`). `github.com`/`api.github.com`/`raw.githubusercontent.com` are `path_default: deny` with allowlists. Symptom of a block: HTTP 403 or NXDOMAIN. Surface to user; don't work around.
- Image ships only CPython 3.14. uv fetches 3.11 (project) and 3.13 (Serena pyright launcher `uvx -p 3.13`) on demand from `github.com/astral-sh/python-build-standalone/releases/download/` (allowed; redirects to `release-assets.githubusercontent.com`).
- `UV_PYTHON_INSTALL_DIR=/home/clawker/.local/share/uv/python` set via `agent.env` because the python stack's default `/usr/local/share/uv/python` is root-owned sticky → `uv python install` EPERM on minor-version symlink (schmitthub/clawker#506). If `uv sync` fails with EPERM, check this env var.
- `.venv`, `__pycache__`, `.pytest_cache`, `.ruff_cache` are tmpfs-masked (`.clawkerignore`) → empty every start; run `uv sync` first.
- Serena LS failing at start = usually the interpreter fetch; log at `~/.serena/logs/<date>/`.
- `gh` GraphQL (`/graphql`) not allowlisted → `gh issue|pr` subcommands 403; REST via `gh api repos/schmitthub/...` works.
- `post_init` (MCP registration) runs once per config volume; changes need volume reset.
