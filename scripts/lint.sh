#!/usr/bin/env bash

set -euo pipefail
set -x

# Resolve the project and its locked dev tools consistently from hooks or CI.
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

uv run --frozen mypy app
uv run --frozen ruff check app scripts tests .github/scripts .semgrep
uv run --frozen ruff format --check app scripts tests .github/scripts .semgrep
