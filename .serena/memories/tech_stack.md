# Tech stack

- Python **3.11** (`.python-version`, `requires-python >=3.11`); uv 0.12.x, `uv_build` backend
- Runtime pins (exact `==`): fastapi 0.128.0, uvicorn 0.38.0, PyJWT 2.12.0, requests 2.31.0, httpx 0.27.0 — duplicated in `requirements.txt` and `pyproject.toml`
- uv `dev` group = ruff only. Security tooling is pre-commit-managed (prek runner, `uv tool install prek`): gitleaks 8.30.1, bandit 1.9.4 (`[tool.bandit]` in pyproject, skips B101), semgrep 1.156.0 (`semgrep/pre-commit` repo; pinning it in uv is impossible — its `mcp` dep needs httpx>=0.27.1 vs runtime httpx==0.27.0), osv-scanner 2.5.1 (golang hook). PyPI `osv-scanner` is a 0.0.1 placeholder — never use it.
- Tests: stdlib `unittest` + `fastapi.testclient` (no pytest)
- Container: `python:3.11-slim`, pip from `requirements.txt`, uvicorn on :8000
- Supply chain tooling on host image: syft, cosign, gh (build-time installs in `.clawker.yaml`)
- Semgrep CI image pinned by digest in `security.yml`; gitleaks CI pinned by `GITLEAKS_VERSION` + checksum; both must equal the hook `rev`s
