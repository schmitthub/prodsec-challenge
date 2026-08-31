# prodsec-challenge — core

Senior ProdSec take-home. `app/` = deliberately vulnerable FastAPI "records API". Deliverable = CI + one custom detection rule (BAC/IDOR) + triage/remediation docs, NOT app fixes. AGENTS.md (= CLAUDE.md symlink) is the human-facing summary; brief at `challenge/candidate-brief.md`, status in `challenge/notes.md`.

## Invariants
- Never patch seeded vulns in `app/` unless explicitly asked. Seeded: IDOR `GET /api/records/{id}` (no owner check — contrast `/notes`), f-string SQL in `db.search_records`, SSRF `POST /api/webhooks/vendor-preview`, `verify_exp: False` + hardcoded `JWT_SECRET` (`app/auth.py`), plaintext passwords `db.USERS`, `repr(exc)` in global handler, fake secrets `config/dev.py`, `helpers/fixture_secrets.py`.
- Commits must pass pre-commit; `.claude/hooks/git-checks.sh` blocks bypass flags. Never route around.
- Two dep surfaces kept in sync: `requirements.txt` (README/CI/Dockerfile) and `pyproject.toml`+`uv.lock` (runtime + `dev` tooling group).

## Source map
- `app/main.py` app + 4 routers + `/health` + catch-all exception handler
- `app/auth.py` HS256 JWT; `get_current_user` dependency = only auth layer; no central authz — each route self-checks
- `app/db.py` in-memory `USERS`/`RECORDS` dicts; `search_records` = throwaway sqlite per call
- `app/routes/{login,records,search,webhooks}.py`; `app/models.py` `User`, `TokenResponse`
- `tests/test_records.py` unittest + TestClient, happy paths only
- `src/prodsec_challenge/` uv scaffold stub, not the service
- `.github/workflows/`, `.semgrep/`, `.pre-commit-config.yaml` — see `mem:ci/core` for pipeline layout, reusable-workflow permission rules, and clawker-copied scaffolding that is known-wrong

## Further memories
- `mem:tech_stack` — pins, Python version, tooling
- `mem:suggested_commands` — dev/test/scan commands
- `mem:conventions` — code + CI style rules
- `mem:task_completion` — what to run before declaring done
- `mem:env/container` — clawker firewall + uv interpreter quirks (read when `uv sync`, Serena LS, or network fails)
