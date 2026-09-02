# Triage

## Code Security Issues

- [dev.py:1](../../config/dev.py#L1) hardcoded dev api key. switch to env var. recommendation leverage `python-dotenv` or `pydantic-settings`, commit sample .env file
- [fixture_secrets.py:3](../../helpers/fixture_secrets.py#L3) secret import gate is brittle and will cause failures if pytest specifically isn't used, and it appears its not. it also should realistically moved to the test harness and be kept out of prod code entirely. also unused so recommend removing if not needed
- [auth.py:11](../../app/auth.py#L11) `JWT_SECRET` hardcoded secret. use secrets.token_urlsafe(32) for dev environment, env var for prod. recommendation move to `pydantic-settings` or use `python-dotenv` with default fallback
- [auth.py:34](../../app/auth.py#L34) `options={"verify_exp": False}` allows for infinite token validity with no way to revoke. recommendation to remove this option and enforce token expiration.
- [webooks.py:25](../../app/routes/webhooks.py#L25) `PreviewRequest.callback_url` exposes SSRF and returns the response from the callback URL. recommendation use a whitelist enum
- [login.py:18](../../app/routes/login.py#L18) user and password conditional is technically vuln to timing attacks but not sure if it's out of scope due to the DB being faked for the purpose of the challenge. if this is going to be kept then consider using a constant time comparison function such as `secrets.compare_digest`
- [search.py:17](../../app/routes/search.py#L17) broken access control. only checks if user is authenticated, not if they have permission to access specific records. recommendation pass current user id to func and check against owner_user_id in DB
- [db.py:78](../../app/db.py#L78) sql injection in search_records. need a sanitization function or use parameterized queries to prevent injection.
- [records.py:27](../../app/routes/records.py#L27) broken access control. only checks if user is authenticated, not if they have permission to access specific records. recommendation pass current user id to func and check against owner_user_id in DB
- [Dockerfile:15](../../Dockerfile#L15) runs as root user. recommendation to create a non-root user and switch to it in the Dockerfile for better security.
- [main.py:26](../../app/main.py#L26) `repr(exc)` is leaking sensitive information to an attacker. recommendation to log the exception securely and return a generic error message to the client, or set env var so that its only displayed locally during development and generic in prod

### False Positive

- [fixture_secrets.py:7](../../helpers/fixture_secrets.py#L7) has a test only key. if this key is truly test only it can be left, but it is much better to use generated keys dynamically within the test itself rather than hardcoding them if possible

## Package Vulnerabilities

| OSV URL                             | CVSS | ECOSYSTEM | PACKAGE   | VERSION | FIXED VERSION | SOURCE  | REACHABLE?  | LIKELIHOOD | IMPACT | NOTES |
|-------------------------------------|------|-----------|-----------|---------|---------------|---------|-------------|------------|--------|-------|
| https://osv.dev/PYSEC-2026-175      | 4.2  | PyPI      | pyjwt     | 2.12.0  | 2.13.0        | uv.lock | no  | none | an attacker can forger arbitrary internal calls as this service | If the app becomes a resource server, it will requires PyJWKClient functionality and need to use PyJWKClient and will be vulnerable if an attacker can ever influence the jku URL ingestion path |
| https://osv.dev/PYSEC-2026-176      | 5.4  | PyPI      | pyjwt     | 2.12.0  | 2.12.1        | uv.lock | no | none | basically an attacker can use blacklisted algorithms, but not forge tokens without access to a private key | If the app becomes a resource server an attacker who controls a registered JWK/JWKS private key can get around the algo allow list because sig verification is performed with the algorithm bound to the PyJWK object instead of the header algorithm  |
| https://osv.dev/PYSEC-2026-177      | 3.7  | PyPI      | pyjwt     | 2.12.0  | 2.13.0        | uv.lock | no | none | attacker can trigger a tight outbound request endless loop if JWKS entpoint is down | Not a resource server... yet... |
| https://osv.dev/PYSEC-2026-178      | 5.3  | PyPI      | pyjwt     | 2.12.0  | 2.13.0        | uv.lock | no | none | unathenticated DoS | attacker can hit the b64 check, but not the detached-payload branch behind it |
| https://osv.dev/PYSEC-2026-179      | 7.4  | PyPI      | pyjwt     | 2.12.0  | 2.13.0        | uv.lock | no | none | an attacker can trigger algo confusion and sign their own tokens | if asymmetric algorithm is ever added to the algo list this will be a problem since HS256 is used so this is a time bomb. should be fixed or CI gates added restricting use of asymmetric algorithms alonside HMAC |
| https://osv.dev/PYSEC-2026-1872     | 5.3  | PyPI      | requests  | 2.31.0  | 2.32.4        | uv.lock | no | none | if .netrc creds are every leveraged it will result in them being leaked in requests | the SSRF with requests lib right now does expose this possibility, should fix ot be cautious, if patching is a problem the workaround is `trust_env=False` |
| https://osv.dev/PYSEC-2026-1873     | 5.6  | PyPI      | requests  | 2.31.0  | 2.32.0        | uv.lock | no | none | tls verification bypass persistence can lead to MiTM attacks | sessions aren't leveraged in this code base |
| https://osv.dev/PYSEC-2026-2275     | 5.5  | PyPI      | requests  | 2.31.0  | 2.33.0        | uv.lock | no | none | malicious file load | normal use of requests is safe. extract_zipped_paths must be called which is an edge case for this lib |
| https://osv.dev/PYSEC-2026-161      | 6.5  | PyPI      | starlette | 0.50.0  | 1.0.1         | uv.lock | yes | low | potential login bypass | currently app makes zero trust decisions on request.url/.pat. Any future code that authorizes/redirects on request.url.path auth middleware, url_for, host-based routing |
| https://osv.dev/PYSEC-2026-2280     | 5.3  | PyPI      | starlette | 0.50.0  | 1.1.0         | uv.lock | no | none | usafe reflection | non issue for this code base, normal use of fastapi doesn't expose this underlying vuln |
| https://osv.dev/PYSEC-2026-2281     | 7.5  | PyPI      | starlette | 0.50.0  | 1.1.0         | uv.lock | no | none | ssrf | if StaticFiles is every used in the future, highly unlikely for an API already, and also from a Windows env. not a problem |
| https://osv.dev/PYSEC-2026-248      | 5.3  | PyPI      | starlette | 0.50.0  | 1.3.0         | uv.lock | no | none | network | if request whitelisting is ever needed this can lead to a confused deputy attack when relying on request.url, request.url.netloc, or request.url.hostname. probably should fix |
| https://osv.dev/PYSEC-2026-249      | 7.5  | PyPI      | starlette | 0.50.0  | 1.3.1         | uv.lock | no | none | DOS | endpoints accept `application/x-www-form-urlencoded` but do not use the vulnerable method |
