---
applyTo: "**/*.py"
---

# Python and FastAPI Security Review

## Purpose

Continue the normal review of correctness, maintainability, performance, and tests. Treat the checks below as additional high-priority security concerns for changed code and security behavior affected by the change.

For each security finding, identify the attacker-controlled input or trust boundary, the vulnerable operation, the resulting impact, a concrete Python/FastAPI remediation, and the relevant missing regression test. Use unchanged code only to establish the changed behavior's impact. Do not report a speculative issue without a plausible attack or missing-control path.

## Broken Access Control

- Require protected routes to derive identity from `current_user: Annotated[User, Depends(get_current_user)]`; never trust a body, path, query, or header value for the caller's user ID or role.
- For every object read, update, delete, and nested-resource operation, verify ownership or an explicitly allowed role before returning data or performing the action. Scope collection queries to the authenticated user unless the route explicitly permits broader access.
- Follow the existing non-enumerating object pattern: return the same 404 response for a missing resource and a resource the caller may not access.

```python
record = db.get_record(record_id)
if record is None or (
    current_user.role != "staff" and record["owner_user_id"] != current_user.id
):
    raise HTTPException(status_code=404, detail="Record not found")
```

## Injection

- Trace request bodies, path/query parameters, and headers into SQL, subprocesses, templates, file paths, and response headers. Pydantic type validation does not make an interpolated interpreter string safe.
- Use SQLite placeholders with parameters passed separately; never construct SQL with f-strings, `%`, `.format()`, or concatenation.
- Invoke subprocesses with an argument list and `shell=False`. Prefer explicit allowlists when user input selects commands, templates, paths, or header values.

```python
rows = connection.execute(
    "SELECT * FROM records WHERE summary LIKE ?", (f"%{term}%",)
).fetchall()
```

## Server-Side Request Forgery

- Treat every caller-controlled URL reaching `requests`, `httpx`, or another outbound client as tainted. `HttpUrl` validates syntax; it does not prevent SSRF.
- Prefer an exact allowlist of HTTPS scheme, hostname, and port. Reject URL credentials and every resolved loopback, private, link-local, reserved, multicast, or metadata-service address for IPv4 and IPv6. Ensure the address checked is the address used for the connection.
- Disable redirects or repeat the full scheme, host, port, and resolved-address validation for every redirect destination. Do not forward inbound authorization, cookies, or other sensitive headers.
- Require connect/read timeouts, bounded streamed response reads, and a centralized outbound-request helper when more than one call site needs the policy. Treat network egress controls as defense in depth, not a replacement for application validation.

```python
response = requests.get(
    validated_url,
    timeout=(2, 5),
    allow_redirects=False,
    stream=True,
)
```

## JWT Anti-Patterns

- Load signing and verification keys from runtime secret configuration. Never hardcode keys or derive the accepted algorithm from an untrusted token header.
- Decode with a fixed server-side algorithm allowlist, signature and expiration verification enabled, and required `sub`, `iat`, and `exp` claims. Validate expected issuer and audience whenever the service issues those claims; allow only small, justified clock-skew leeway.
- Reject disabled verification, including `verify_signature=False` or `verify_exp=False`, excessive token lifetimes, and use of unverified claims for authorization.
- Convert PyJWT validation failures to a generic FastAPI 401 response with `WWW-Authenticate: Bearer`. Never return the validation exception or log the token.

```python
claims = jwt.decode(
    token,
    signing_key,
    algorithms=[JWT_ALGORITHM],
    options={"require": ["sub", "iat", "exp"]},
)
```

## Sensitive Information Disclosure

- Use response models or typed allowlists for sensitive resources so internal fields are not serialized accidentally. Return only explicitly selected metadata from dependencies and upstream services.
- Keep client-facing authentication and exception messages generic. Do not return exception representations, stack traces, SQL details, internal paths, credentials, tokens, configuration values, or sensitive record fields.
- Log unexpected exceptions server-side with safe context, then return a fixed error response. Ensure authentication failures do not reveal whether an account exists.

```python
logger.exception("unhandled_request", extra={"path": request.url.path})
return JSONResponse(status_code=500, content={"error": "internal_error"})
```

## Insufficient Security Logging

- Require auditable events for authentication and token failures, authorization denials, privileged actions, blocked outbound destinations, and unexpected exceptions. Do not require noisy success logs for ordinary reads unless they are security-sensitive.
- Use `logging.getLogger(__name__)` and structured context fields such as event, actor ID, action, resource ID, outcome, and an available request correlation ID.
- Never log passwords, JWTs, signing keys, API keys, cookies, raw request bodies, sensitive record contents, or full URLs that may contain credentials or secret query values.

```python
logger.warning(
    "authorization_denied",
    extra={"actor_id": current_user.id, "action": "read", "resource_id": record_id},
)
```

## Missing Security Invariant Tests

- When a feature adds or expands a trust boundary, protected resource, privileged operation, token flow, interpreter sink, outbound request, sensitive response, or security event, require the applicable negative invariant tests in addition to happy paths. Do not demand unrelated security tests.
- For protected routes, test unauthenticated access, cross-user identifiers, disallowed roles, nested resources, and every state-changing method. New authenticated `GET` routes must remain covered by the OpenAPI-driven invariant in `../../tests/test_authz_invariant.py`; any exemption must be narrow and justified.
- For JWT changes, test malformed, invalid-signature, expired, missing-claim, wrong-issuer, and wrong-audience tokens as applicable. Assert generic 401 responses.
- For injection-sensitive changes, prove adversarial input remains data rather than executable syntax. For outbound requests, mock network and DNS behavior and cover allowed hosts, loopback/private/link-local/metadata addresses, IPv6, redirects to blocked destinations, timeouts, and response-size limits.
- For disclosure and logging changes, assert public responses omit internal details and use `unittest.TestCase.assertLogs` or a mocked logger to verify required events without secret or sensitive values.

These checks supplement the general code review. Continue reporting non-security correctness, reliability, maintainability, performance, and test issues.
