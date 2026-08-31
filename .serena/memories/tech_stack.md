# Tech stack

- Python **3.11** (`.python-version`, `requires-python >=3.11`); uv 0.12.x, `uv_build` backend
- Runtime pins (exact `==`): fastapi 0.128.0, uvicorn 0.38.0, PyJWT 2.12.0, requests 2.31.0, httpx 0.27.0 — duplicated in `requirements.txt` and `pyproject.toml`
- Dev group (`uv sync` installs): ruff, bandit (`[tool.bandit]` in pyproject, skips B101, excludes tests/.venv), semgrep, osv-scanner, prek (pre-commit runner)
- Tests: stdlib `unittest` + `fastapi.testclient` (no pytest)
- Container: `python:3.11-slim`, pip from `requirements.txt`, uvicorn on :8000
- Supply chain tooling on host image: syft, cosign, gh (build-time installs in `.clawker.yaml`)
- Semgrep CI image pinned by digest in `security.yml`; version must equal comment in `.pre-commit-config.yaml`
