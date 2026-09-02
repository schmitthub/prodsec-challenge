# Lens: authentication

Identity establishment and session state. Missing authentication on a protected surface
(CWE-306), token and session validation (CWE-287, CWE-347, CWE-613), password storage and
comparison (CWE-256, CWE-916, CWE-208), account enumeration and brute force (CWE-307),
credential handling in transit and at rest.

Read `_common.md` first.

## Worklist

1. `auth-model.md`: the intended identity model, which surfaces are meant to be
   unauthenticated.
2. `route-map.md`: the `authenticated` and `dependencies` columns. Any route outside the
   declared unauthenticated set with no auth dependency is a finding. New routers count.
3. `findings.json`: scanner rules about hardcoded passwords, weak hashes, JWT options.
4. Changed code in login, token issue/verify, password, session, middleware, and any
   dependency that yields the current user.

## Look for

**Tokens and sessions**
- Signature or expiry verification disabled or optional; algorithm not pinned; algorithm
  list mixing symmetric and asymmetric; audience or issuer issued but not checked.
- No lifetime, or a lifetime long enough that leak = permanent access, with no revocation.
- Session fixation, session id in URL, tokens accepted from query strings.
- Identity read from a header, cookie or body that the server does not sign.

**Passwords and credentials**
- Plaintext storage or comparison; fast unsalted hashes for passwords.
- Timing-unsafe comparison of secrets; rate as `low` unless the compared value is
  high-value and the comparison is network-observable.
- Different status, body or timing for unknown user vs wrong password.
- No lockout, throttling or proof-of-work on login, reset, OTP or token-exchange routes.
- Credentials or tokens in logs, error messages, URLs, or response bodies.

**Missing authentication**
- A route or router mounted without the auth dependency; a middleware bypass (path prefix
  allowlist, method allowlist) that admits protected paths; health or metrics routes that
  reveal more than liveness.

## Severity

| situation | severity |
|---|---|
| signature not verified, or algorithm confusion possible | critical |
| protected surface reachable with no authentication | high |
| identity trusted from unsigned client data | critical |
| no expiry and no revocation on bearer credentials | high |
| plaintext password storage | high |
| enumeration, timing, missing throttling | low–medium |

## Not findings

- Where the signing secret lives and how strong it is: `secrets-crypto`.
- Whether an authenticated user may reach a given object: `access-control`.
- Fixture credentials for a fake or test-only store, as declared in `repo-conventions.md`.
