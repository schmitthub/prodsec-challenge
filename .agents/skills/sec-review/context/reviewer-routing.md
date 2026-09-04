# Reviewer routing — records-api

Use this map to build candidates from repository paths, then confirm them against the code or
diff. `general` is mandatory for every non-empty review and is not repeated in the tables.

## Application paths

| path | primary specialist candidates | add only when the change contains this signal |
|---|---|---|
| `app/api/deps.py` | `authentication`, `access-control` | `secrets-crypto` for JWT algorithms/key use; `data-exposure` for auth error behavior |
| `app/api/main.py` | `access-control`, `authentication` | `web-platform` when router prefixes or HTTP policy change |
| `app/api/routes/login.py` | `authentication` | `data-exposure` for enumeration/error shape; `input-validation-dos` for request limits or brute-force controls; `web-platform` for cache/cookie/header behavior |
| `app/api/routes/records.py` | `access-control` | `data-exposure` for response/error shape; `input-validation-dos` for pagination/identifier bounds; `business-logic` for writes or state transitions |
| `app/api/routes/search.py` | `access-control`, `injection`, `input-validation-dos` | `data-exposure` when result fields or error details change |
| `app/api/routes/webhooks.py` | `outbound-requests`, `access-control` | `data-exposure` for reflected upstream data/errors; `input-validation-dos` for URL/response bounds; `web-platform` for redirects or header handling |
| `app/main.py` | `web-platform`, `data-exposure` | `authentication` or `access-control` when API mounting or global dependencies change |
| `app/models.py` | `input-validation-dos`, `access-control` | `data-exposure` for public response fields; `business-logic` for ownership, role, uniqueness, or state fields |
| `app/crud.py` | `access-control`, `injection`, `business-logic` | `authentication` or `secrets-crypto` for user/password operations |
| `app/core/security.py` | `authentication`, `secrets-crypto` | — |
| `app/core/config.py` | `secrets-crypto`, `web-platform`, `outbound-requests` | `input-validation-dos` for parser/size validation |
| `app/core/db.py` | `business-logic`, `injection` | `authentication` or `secrets-crypto` for seeded users/passwords; `access-control` for ownership assignment |
| `app/alembic/**` | `business-logic` | `injection` for raw SQL; `access-control` for tenant/owner keys; `data-exposure` for sensitive columns |
| `app/{backend_pre_start,tests_pre_start,initial_data}.py` | `business-logic` | `injection` for constructed statements/commands; `secrets-crypto` for credential handling |

For a whole route directory, use the union of the relevant route rows, rank direct reachable
boundaries first, and keep only four specialists alongside `general`.

## Tests and tooling

| path | specialist candidates |
|---|---|
| `tests/api/routes/test_login.py`, `tests/crud/test_user.py` | `authentication`; add `data-exposure` for enumeration/error assertions |
| `tests/api/routes/test_records.py`, `tests/api/routes/test_search.py`, `tests/api/test_authz_invariant.py`, `tests/crud/test_record.py` | `access-control`; add `injection` or `input-validation-dos` when those controls are exercised |
| `tests/api/routes/test_webhooks.py` | `outbound-requests`, `access-control`; add `data-exposure` for preview/error assertions |
| other `tests/**` | mirror the application behavior under test; use `general` alone for ordinary test plumbing |
| `scripts/sarif-scan.sh`, `.github/scripts/**`, scanner configuration | `supply-chain-ci`; add `injection` for attacker-controlled shell/data interpolation |
| `scripts/prestart.sh`, `scripts/tests-start.sh`, `scripts/test.sh` | `supply-chain-ci`; add `injection` or `secrets-crypto` only for matching changes |
| `scripts/badhost-probe.py` | `web-platform`; add `injection` for raw request construction changes |
| `.agents/skills/sec-review/**`, `.claude/**`, `.codex/**` | `supply-chain-ci` when review gates, generated agents, permissions, or execution policy change; otherwise `general` alone |

A test-only change is not automatically low risk. Select the specialist when it removes or
weakens proof of a security invariant, scanner gate, or release identity check.

## Delivery and configuration

| path | primary specialist candidates | add only when the change contains this signal |
|---|---|---|
| `.github/workflows/**`, `.github/actions/**`, `.github/dependabot.yml`, `.github/codeql/**` | `supply-chain-ci` | `secrets-crypto` for credentials/OIDC/TLS; `injection` for untrusted workflow expressions or shell construction |
| `Dockerfile`, `docker-compose.yaml`, `docker-compose.override.yaml`, `.dockerignore` | `supply-chain-ci` | `secrets-crypto` for build/runtime secrets; `web-platform` for exposed HTTP configuration |
| `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml` | `supply-chain-ci` | `secrets-crypto` when crypto/auth dependencies or scanner credentials change |
| `.env.example`, `.clawker.yaml`, deployment/runtime configuration | `secrets-crypto` | `outbound-requests` for egress rules; `web-platform` for origins/hosts/TLS; `supply-chain-ci` for build or agent execution policy |
| `AGENTS.md` and directory guides | select the specialist whose security policy changed; otherwise `general` alone |
| ordinary documentation or generated metadata | `general` alone |

## Content signals that override a broad path match

- Client-controlled identifiers, `user_id`, role checks, response ownership, or mass assignment:
  `access-control`.
- Login, bearer dependencies, JWT claims/expiry/algorithms, password hashing, or credential
  comparison: `authentication`; add `secrets-crypto` when key material or cryptography changes.
- SQL expressions are not automatically injection. Select `injection` for raw text, dynamic
  fragments, unsafe shell/template/path construction, or a changed call chain reaching such a
  sink. Parameterized SQLModel expressions alone do not qualify it.
- `requests`, URL parsing, allowlists, redirects, proxies, callbacks, sockets, or DNS:
  `outbound-requests`.
- Pagination, regex, request/response size, parser depth, timeouts, or rate limits:
  `input-validation-dos`.
- CORS, Host/Origin handling, cookies, CSRF, cache/security headers, OpenAPI exposure, or HTML:
  `web-platform`.
- Exceptions, logs, public models, upstream previews, debug output, or existence oracles:
  `data-exposure`.
- Transactions, retry/idempotency, state machines, unique constraints, audit, or races:
  `business-logic`.
- Uploads, archives, YAML/XML/pickle, temporary files, or symlinks:
  `unsafe-parsing-files`.

Do not select a specialist from a filename alone when the diff does not touch its concern. In path
mode, where there is no diff, the primary candidates own the full-file review. When more than four
specialists remain, rank direct changes to authentication, tenant authorization, outbound egress,
secrets, interpreter sinks, and release identity above secondary hardening concerns; list every
qualified omission in the plan.
