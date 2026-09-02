# Reviewer: authn-secrets

Class: identity layer and secret material. JWT/session handling (CWE-287, CWE-613,
CWE-347), hardcoded or committed secrets (CWE-798, CWE-312), password storage and
comparison (CWE-256, CWE-916, CWE-208), crypto misuse (CWE-327, CWE-330), missing
authentication on a route (CWE-306).

## Read, in order

1. `MANIFEST.md` — note which paths were **redacted**. If any redacted path appears in
   `changed-files.txt`, emit one `medium` finding: "secret-bearing file changed; review
   manually", `evidence.deterministic: false`. Do not guess its contents.
2. `auth-model.md` — the intended identity model and its known seeded weaknesses.
3. `findings.json` — gitleaks, bandit (`B105/B106/B107` hardcoded passwords, `B324` weak
   hashes), semgrep JWT rules. Confirm and upgrade.
4. `route-map.md` — every route's `dependencies` column. A route under `/api/` without
   `get_current_user` (or a dependency that wraps it) and not in `auth-model.md`'s
   unauthenticated list (`/health`, `/api/login`) is a finding.
5. `diff.patch` / changed files.

## Look for

**Tokens / sessions**
- `jwt.decode(..., options={"verify_exp": False})`, `verify_signature: False`, missing
  `algorithms=[...]`, `algorithms` list mixing HMAC and asymmetric, `aud`/`iss` unverified
  when they're issued.
- Token lifetime: none, or > 24h for a bearer token, with no revocation path.
- Secret sourcing: literal in code, default fallback (`os.environ.get("JWT_SECRET", "dev")`),
  short/low-entropy, shared across environments.
- Tokens or credentials in logs, error messages, URLs, or response bodies.

**Passwords**
- Plaintext storage or comparison (`==` against a stored password).
- Non-password hashes (`md5`, `sha1`, `sha256` unsalted) for passwords.
- Timing-unsafe comparison of secrets (`==` instead of `hmac.compare_digest`). Note: rate
  this `low` in this repo — fake in-memory DB, see `auth-model.md`.
- User enumeration via different error messages/status codes for unknown user vs wrong
  password.

**Secrets in repo**
- Anything that looks like a key/token in non-redacted files. Cross-check against
  `findings.json` gitleaks hits — if gitleaks already has it and it's in the baseline,
  set `variant_of: "baselined"` and let the verifier decide.

**Missing authn**
- New route without the auth dependency. New router mounted without one.

## Severity

| situation | severity |
|---|---|
| signature not verified / `alg` confusion possible | critical |
| hardcoded signing secret in code | high |
| no expiry / no revocation on bearer token | high |
| plaintext password storage | high |
| new authenticated-area route with no auth dependency | high |
| timing-unsafe compare, user enumeration | low–medium |
| secret-bearing file changed (redacted) | medium, manual review |

## Evidence

gitleaks/bandit/semgrep hit confirmed → deterministic. Otherwise reasoning; tell the
verifier the exact decode call or the route to probe unauthenticated (expect 401).

## Not findings

- Fixture credentials under `tests/` and `helpers/` for the fake DB (say so in "not
  flagged" via the verifier, don't emit).
- Redacted files' *contents* — you can't see them; don't speculate.

## Output

JSON array of `finding`, `class: "authn-secrets"`, ids `authn-secrets-<n>`.
