# Triage Write-Up

## Real findings I would prioritize

| Priority | Severity | Finding | Rationale |
|---|---|---|---|
| P0 | Critical | Broken access control on `GET /api/records/{record_id}` ([records.py:27](../../app/routes/records.py#L27)) | Only checks that the caller is authenticated, not that they own the record. Any member who knows or can guess a record ID can read another member's health record. This creates immediate risk of impermissible PHI disclosure and material HIPAA/privacy compliance exposure. |
| P0 | Critical | Broken access control on `GET /api/search` ([search.py:17](../../app/routes/search.py#L17)) | Search returns every user's released health records without an ownership or role check; an empty query returns all of them in one request. This is a low-complexity bulk PHI disclosure path with material HIPAA/privacy compliance exposure. |
| P0 | Critical | SQL injection in `search_records` ([db.py:78](../../app/db.py#L78)) | The search term is interpolated directly into the query. Against the modeled production health-record database, any authenticated member could alter the query and plausibly extract unreleased PHI or data from other tables at scale. Integrity, destructive, or broader system impact depends on the production driver and database account permissions. |
| P0 | High | SSRF in `POST /api/webhooks/vendor-preview` ([webhooks.py:25](../../app/routes/webhooks.py#L25)) | A staff caller can make a response-bearing server-side GET to internal services and compatible cloud-metadata endpoints, with the first 200 response characters returned. Broad production network reach makes this immediately urgent. Forging staff access through the hardcoded JWT key is a credible but conditional chain because it also requires repository access and a valid staff user ID; staff authentication, GET-only behavior, and the response cap keep the standalone severity at High. Additionally `requests.get` exceptions are not caught, so DNS, connection, timeout, and TLS failures reach the global handler and are returned through `repr(exc)`. Differences in error details and response timing can disclose internal host and port state for attacker-selected URLs, strengthening the SSRF into an internal network-scanning oracle. |
| P1 | Critical | Hardcoded `JWT_SECRET` ([auth.py:11](../../app/auth.py#L11)) | The production signing key is a string literal in source. Anyone with private-repository access, or a leaked copy of the code, can forge a token for any known valid user ID, including staff, completely bypassing authentication and role checks. The private-repository prerequisite reduces immediate likelihood, not impact. |
| P1 | High | `verify_exp: False` ([auth.py:34](../../app/auth.py#L34)) | The decoder ignores token expiration, so a leaked or forged token remains usable beyond its intended lifetime. This does not prevent global revocation through signing-key rotation or user deletion; the lack of per-token revocation is a separate control gap. |
| P2 | Medium | Exception detail returned to clients ([main.py:26](../../app/main.py#L26)) | `repr(exc)` can disclose query, schema, path, or other internal details and amplify exploitation of the SQL injection. Its independent impact is information disclosure, and useful error content is backend-dependent. |
| P2 | Medium | Container runs as root ([Dockerfile:15](../../Dockerfile#L15)) | Not exploitable alone. Code execution already compromises the application process; root increases post-exploitation access to filesystem contents, mounted secrets, Linux capabilities, and potential container-escape paths. |
| P3 | Low | pyjwt 2.12.0, five advisories (PYSEC-2026-175, -176, -177, -178, -179) | The affected paths are not currently reachable: the app uses no JWKS client and fixes verification to HS256. Track and upgrade the dependency, but a hypothetical future asymmetric configuration does not raise the severity of the current application. |
| P3 | Low | starlette 0.50.0, five advisories (PYSEC-2026-161, -2280, -2281, -248, -249) | The app does not make a security decision from the affected URL parsing, and `request.url.path` is only reflected in the error body. The remaining advisories require `StaticFiles`, `HTTPEndpoint`, form parsing, or `request.url.hostname`, none of which are used. Track the upgrade, currently blocked behind the `fastapi==0.128.0` pin on `starlette<0.51.0`. |
| P3 | Low | requests 2.31.0, three advisories (PYSEC-2026-1872, -1873, -2275) | Not reachable except PYSEC-2026-1872 (`.netrc` leak), which rides the SSRF above and needs a `.netrc` in the image. |

## False positives and acceptable in context

| Finding | Verdict | Rationale |
|---|---|---|
| Hardcoded vendor API key ([dev.py:1](../../config/dev.py#L1)) | False positive | Known seeded value in an unused development config, paired with an `.example.test` endpoint. A live-looking prefix does not establish that a credential is valid. |
| Secret import gate ([fixture_secrets.py:3](../../helpers/fixture_secrets.py#L3)) | Informational | Unused test-only defensive guard. Its location is a code-organization concern, not an exploitable production vulnerability. |
| `FIXTURE_JWT_SECRET` ([fixture_secrets.py:7](../../helpers/fixture_secrets.py#L7)) | False positive | Clearly non-production test value, never imported by the app or tests. |
| Non-constant-time password compare ([login.py:18](../../app/routes/login.py#L18)) | Informational | A Python string-comparison timing difference is not practically exploitable over the network, and both failure branches return the same 401 response. |
| No throttling or lockout on `POST /api/login` ([login.py:15](../../app/routes/login.py#L15)) | Low, track | Unlimited password guesses return an immediate 401 with no `Retry-After`. Brute-force protection is usually, and appropriately, handled at the edge (WAF, gateway, or ingress rate limiting), so this is not an application defect on its own. Worth tracking because a successful guess yields a token that never expires; application-layer account lockout is the next line of defense if edge controls are absent. |
| No application logging or monitoring | Low, track | No request, authentication, or authorization events are logged anywhere in the app, and nothing is emitted for the exception handler beyond the response body. Not exploitable, but it means none of the findings above would be detected in production, incident response has nothing to reconstruct from, and the login and search abuse paths are invisible. Will be a pain point for any real deployment. |

### Pipeline Capabilities

Local hooks catch issues before PR. CI is the enforcement point.

- IDOR regressions: cross-user authorization invariant test fails if one member can read another member's protected resource.
- SQL injection and unsafe code patterns: Semgrep Python/security rules and CodeQL Python analysis.
- Python security footguns: Bandit, gated on new high-severity findings.
- Secrets: Gitleaks full-history scan with baseline, custom rules, and GitHub secret push protection.
- Vulnerable dependencies: Dependency Review for changed dependencies, Dependabot PRs, osv-scanner scanning deterministically using `uv.lock` and build images from `Dockerfile`.
- GitHub Actions risks: Semgrep Actions rules and CodeQL Actions analysis.
- Release integrity: Syft SBOMs, cosign signatures, GitHub attestations, checksums, immutable tags, and branch/tag rulesets.
- Human review gaps: required reviewers, Copilot review instructions, lazy loading agent memory files, and the security-review agent skill for logic/intent issues scanners miss.

### Pipeline Gaps

- The pipeline is intentionally stacked with different static analysis tools since they can all shine in different areas and offer complementary coverage. But static analysis is a labor of love and can't know design intent. This is mitigated with agentic AI skills and instructions.
- The SCA tooling cannot detect reachability. AI can assist here as well.
- gitleaks secrets detection thresholds are set to lower noise, but will miss lower entropy password assignments, bandit does a decent job of assisting here but only for python code.

## Next Steps

The project needs to adopt more idiomatic python and FastAPI design patterns and coding styles, which will also make security easier.

- Better data model design. Stricter data contracts lead to fewer surprises, for example when returning data from API endpoints.
- A real DB backend. Switching to an ORM like SQLModel will help manage database interactions more safely and efficiently. Migrations and fixtures can pre-seed the DB locally so that test users can be removed from source
- A testing framework like pytest with fixtures, mocks, and generators for more robust testing opportunities.
- Adopt a modern python package manager so that a lockfile can be persisted for deterministic builds and a dependency graph for scanners, I took the liberty of adding `uv` to improve scanner accuracy for the review but persisted `requirements.txt`.
- For better broken access control detection use scope deps (e.g. `Depends(authorize_record)` or a role dep) is a better way to describe intent with self documenting code. Deterministic, framework-level, no pattern matching.
- All secrets and configs need to be centralized and env var backed. I like `pydantic-settings` it pairs nicely with FastAPI, but `python-dotenv` is a start.
- Auth needs to be decoupled from the application and operate as a resource server. The JWT implementation will then need to be more robust and include properties like `aud`, `iss`, `resource` to ensure proper validation and security.
- Implement comprehensive logging and monitoring to detect and respond to security incidents
- Common oversight is making sure FastAPI's default /docs, /redocs, and /openapi.json endpoints are properly secured or disabled in production environments to prevent information leakage. This doesn't have to be at the app level and can be handled through reverse proxies or API gateways as well.
