# Triage Write-Up

## Real findings I would prioritize

| Priority | Severity | Finding | Rationale |
|---|---|---|---|
| P0 | High | Broken access control on `GET /api/records/{record_id}` ([records.py:27](../../app/routes/records.py#L27)) | Only checks that the caller is authenticated, not that they own the record. Any member who knows or can guess a record ID can read another member's health record. This creates immediate risk of impermissible PHI disclosure and material HIPAA/privacy compliance exposure, but the record-at-a-time scope keeps its standalone severity below the bulk search flaw. |
| P0 | Critical | Broken access control on `GET /api/search` ([search.py:17](../../app/routes/search.py#L17)) | Search returns every user's released health records without an ownership or role check; an empty query returns all of them in one request. This is a low-complexity bulk PHI disclosure path with material HIPAA/privacy compliance exposure. |
| P1 | Critical | Hardcoded `JWT_SECRET` ([auth.py:11](../../app/auth.py#L11)) | The production signing key is a string literal in source. Anyone with private-repository access, or a leaked copy of the code, can forge a token for any known valid user ID, including staff, completely bypassing authentication and role checks. The private-repository prerequisite reduces immediate likelihood, not impact. |
| P1 | High | `verify_exp: False` ([auth.py:34](../../app/auth.py#L34)) | The decoder ignores token expiration, so a leaked or forged token remains usable beyond its intended lifetime. This does not prevent global revocation through signing-key rotation or user deletion; the lack of per-token revocation is a separate control gap. |
| P0 | High | SSRF in `POST /api/webhooks/vendor-preview` ([webhooks.py:25](../../app/routes/webhooks.py#L25)) | A staff caller can make a response-bearing server-side GET to internal services and compatible cloud-metadata endpoints, with the first 200 response characters returned. Broad production network reach makes this immediately urgent. Forging staff access through the hardcoded JWT key is a credible but conditional chain because it also requires repository access and a valid staff user ID; staff authentication, GET-only behavior, and the response cap keep the standalone severity at High. |
| P0 | Critical | SQL injection in `search_records` ([db.py:78](../../app/db.py#L78)) | The search term is interpolated directly into the query. Against the modeled production health-record database, any authenticated member could alter the query and plausibly extract unreleased PHI or data from other tables at scale. Integrity, destructive, or broader system impact depends on the production driver and database account permissions. |
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

## Pipline Overview

The pipeline has local and remote variants. In practice I have experienced that developers greatly appreciate and achieve higher adoption, enthusiasm, and fix velocity when they can integrate the same or similar tooling into their local workflows. They are already running local toolchains for linting, testing, and static analysis, so adding security checks to this workflow minimizes context switching and encourages early detection and remediation of issues. The remote pipeline serves as a centralized enforcement and verification mechanism, ensuring consistency and catching any issues that might have been missed locally. The local pipeline is opt in only if they install `prek` or `pre-commit` and the git hooks. Local also has a convenience script for `prek` users to generate sarif files in `.sarif/` which most IDEs and sarif plugins will automatically pickup to give syntax highlighting and inline feedback for security issues. Some of what I did is duplicated between github

The stack contains:
# TODO: this needs to be reduced to a concrete inventory of what can be detected
- Cross user test invariant
- semgrep for static analysis
- bandit for static analysis
- osv-scanner for python dependency and container vulnerability scanning
- gitleaks for secret detection
- codeql runs in CI as well, custom configuration committed for tuning analysis behavior
- Tag for release workflow (git trunk, for a gitflow or other strat this would be adapted) that uses syft and cosign to generate signed SBOMs and release artifacts. I also included github attestations for SLSLA 3-esque attestation. Build provenance is important for supply chain security. CD gates can enforce verification of these artifacts before deployment and ensure the build artifacts came from the CI environment instead of being circumvented by a malicious actor (axios is a recent example of what this could have mitigated)
- Github Advanced Security secrets push rejection
- Dependabot for automated dependency updates with custom configuration file committed for tuning dependency update behavior. Opens PRs for python, docker, and GitHub Actions workflows.
- Immutable tagging
- Tag and branch rulesets to require reviewers, commit signing, and control merge strategies included
- Git copilot code review instructions
- A harness agnostic loose agent skill for tailored security reviews

### Pipeline Gaps

- The pipeline is intentionally stacked with different static analysis tools since they can all shine in different areas and offer complementary coverage, reducing the likelihood of missing security issues. But static analysis is a labor of love and can't know intent. So the intent is not to exhaust, its to provide a team with options
- The SCA tooling cannot detect reachability, but some enterprise solutions do couple their SCA with static analysis to achieve this

## Next Steps

The project is not a matured python or FastAPI project.

- Needs a real DB backend
- Needs to use pytest with fixtures, mocks, and generators for more robust testing
- Needs to adopt a modern python package manager so that a lockfile can be persisted for deterministic builds and a dependency graph for scanners, I took the liberty of adding `uv`  already but persisted `requirement.txt`.
- For better broken access control detection using scope deps (e.g. `Depends(authorize_record)` or a role dep) is a better way to describe intent with self documenting code
- All secrets and configs need to be centeralized and env var backed. I like `pydantic-settings` it pairs nicely with FastAPI, but `python-dotenv` is a start.
- Auth needs to be decoupled from the application and operate as a resource server. The JWT implementation will then need to be more robust and include properties like `aud`, `iss`, `resource` to ensure proper validation and security.
