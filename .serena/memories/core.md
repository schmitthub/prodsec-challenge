# prodsec-challenge — core

Postgres-backed FastAPI records service with SQLModel/Alembic persistence, OAuth2 bearer auth, security-focused CI, and signed release artifacts.

## Invariants
- Security behavior is deliberate: preserve expiring HS256 tokens, bcrypt password storage, owner-scoped record/search access, staff-or-owner note access, exact-host HTTPS webhook allowlisting, redirect refusal, and foreign-resource 404 responses.
- Schema changes use Alembic; `app/core/db.py:init_db` only seeds idempotent local fixtures.
- `pyproject.toml` + `uv.lock` are dependency truth. `requirements.txt` and `Dockerfile.old` are legacy.
- Commits must pass configured hooks; never bypass the git guards.

## Source map
- `app/main.py`: FastAPI assembly, CORS, versioned API mount, health, catch-all handler.
- `app/authz/`: reusable symbolic authorization contracts and live route discovery; see `mem:design/access-control-deps` for the accepted design and verification.
- `app/api/policies/`: reviewed application policy symbols and provider implementations. RecordBase/RecordNoteBase name protected asset families; RecordPage/RecordNotes are typed provider payloads. Route response schemas remain independent.
- `app/api/deps.py`: SQLModel session and current-user authentication only.
- `app/api/main.py` + `app/api/routes/`: login, identity, records/notes, search, webhook preview.
- `app/core/config.py`: environment settings, Postgres DSN, allowlist parsing, non-local secret validation.
- `app/core/db.py`: engine and local fixture seeding; `app/core/security.py`: JWT/bcrypt.
- `app/models.py`: SQLModel tables/public schemas/enums/token models; `app/crud.py`: create/authenticate helpers.
- `app/alembic/`: migration runtime and versions.
- `tests/`: pytest against real Postgres; API, authorization invariant, CRUD, startup, and factory coverage.
- `scripts/lint.sh`: shared pre-commit/CI mypy + Ruff checks, configured in pyproject.toml and locked in uv.lock; catches mutable policy override narrowing and weak annotations/suppressions.
- `.github/workflows/` + `.pre-commit-config.yaml`: CI/security/release automation; see `mem:ci/core`.

## Agent docs
Every source-bearing directory under `app/`, `scripts/`, and `tests/` has a local `AGENTS.md` and sibling relative `CLAUDE.md -> AGENTS.md`. The nearest guide owns direct-file symbol inventory; parent guides summarize children.

## Further memories
- `mem:tech_stack` — runtime/tool pins and dependency surfaces.
- `mem:suggested_commands` — setup, database, test, lint, and scan commands.
- `mem:conventions` — application, test, CI, and agent-doc conventions.
- `mem:task_completion` — proportional verification checklist.
- `mem:env/container` — container egress and interpreter details.
