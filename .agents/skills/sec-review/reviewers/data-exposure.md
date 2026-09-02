# Reviewer: data-exposure

Class: information leaking to the wrong party. Error handlers and stack traces (CWE-209,
CWE-497), over-broad response models (CWE-200), sensitive data in logs (CWE-532), debug
endpoints/docs in production (CWE-489), verbose 404-vs-403 oracles (CWE-204), CORS and
security headers (CWE-942, CWE-1021).

## Read, in order

1. `MANIFEST.md`, `auth-model.md`.
2. `findings.json` — bandit `B110` (pass on except), semgrep error-handling rules.
3. `route-map.md` — response models. A handler returning a raw dict/ORM object instead of a
   declared `response_model` is where over-exposure hides.
4. `diff.patch` / changed files, plus `app/main.py` on `--full` (global handlers, middleware,
   docs settings).

## Look for

**Errors**
- Global exception handler returning `str(exc)`, `repr(exc)`, `traceback.format_exc()`, or
  the exception class name to the client.
- `HTTPException(detail=<internal state>)` — SQL text, file paths, hostnames, user ids of
  *other* users.
- Different status/body for "not found" vs "not yours" on tenant-scoped resources. In this
  service, the correct answer for a record you don't own is the same as for one that doesn't
  exist (see `auth-model.md`). This is a leak, not access control — `access-control` owns
  the missing check, you own the oracle.

**Responses**
- Returning `User` objects that include password/hash/secret fields; returning full records
  when only a subset is needed; list endpoints echoing `owner_id` of others.
- Pydantic models with `password` or token fields and no `exclude`.

**Logging**
- Request bodies, `Authorization` headers, tokens, passwords, or PII in `print`/`logging`.

**Surfaces**
- `/docs`, `/redoc`, `/openapi.json` enabled with no environment gate — `low` here (dev
  service), note it.
- `debug=True`, `--reload` in the Dockerfile `CMD`.
- CORS `allow_origins=["*"]` with credentials.

**Outbound**
- SSRF responses (`webhooks`) echoed back to the caller: body, headers, status of an internal
  host. That turns blind SSRF into full-read SSRF — flag it here and cross-reference the
  `injection` class in `variant_of`.

## Severity

| situation | severity |
|---|---|
| exception repr/traceback to client | medium (high if it can include secrets or SQL) |
| credentials/tokens in logs or responses | high |
| SSRF response body echoed to caller | high |
| 404/403 oracle on tenant resources | low |
| docs/debug exposed | low |

## Evidence

bandit/semgrep hit → deterministic. Otherwise reasoning; give the verifier a request that
triggers the handler (e.g. `GET /api/records/not-an-int`, or a search query that breaks SQL).

## Not findings

- `HTTPException(status_code=404, detail="Record not found")` — generic, fine.
- Logging at `debug` level with no PII.

## Output

JSON array of `finding`, `class: "data-exposure"`, ids `data-exposure-<n>`.
