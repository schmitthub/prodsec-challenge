# Auth model — records-api

Treat this hand-maintained file as the authorization ground truth. A code change that
contradicts it is a finding; a new resource not described here requires an explicit policy
decision rather than an invented reviewer assumption.

## Identity

- The API prefix is `settings.API_V1_STR` (default `/api/v1`).
- `POST <prefix>/login` accepts an OAuth2 password-grant form. `app/crud.py:authenticate`
  looks up the email and verifies the submitted password against bcrypt.
- `app/core/security.py:create_access_token` signs an HS256 JWT whose `sub` is the user UUID
  and whose `exp` is an absolute UTC expiry.
- `app/api/deps.py:decode_oauth2_token` accepts only the configured HS256 algorithm and relies
  on PyJWT's normal expiry validation. `get_current_user` resolves `sub` to the database
  `User`; `CurrentUser` is the route dependency.
- `app/api/deps.py:get_current_staff_user` is the staff role gate. `RecordDep` is currently
  an unused bearer-token alias and does not authenticate a route by itself.
- Roles are `member` and `staff`. Role and identity used for authorization must come from
  the token-derived `CurrentUser`, never from request data.
- Public framework/service endpoints are `/health`, `/docs`, `/redoc`, and
  `<prefix>/openapi.json`; the login route is also unauthenticated by design. All business
  routes require `CurrentUser` directly or through `get_current_staff_user`.

Authentication failures must not disclose whether an email exists. Successful and rejected
token responses carry `Cache-Control: no-store` and `Pragma: no-cache`.

## Resources and expected scope

| resource/action | who may read or invoke | who may write | required behavior |
|---|---|---|---|
| current user via `GET <prefix>/me` | the authenticated user | nobody through the API | identity comes only from `CurrentUser` |
| record list and `GET <prefix>/records/{record_id}` | owner only | no record write route currently exists | every query/lookup is bound to `current_user.id` |
| record search via `GET <prefix>/search` | owner only, including staff users' own records | — | count and page use the same owner and search filters |
| record notes via `GET <prefix>/records/{record_id}/notes` | record owner or any staff user | no note write route currently exists | missing and unauthorized records both return the same 404 |
| vendor preview via `POST <prefix>/webhooks/vendor-preview` | staff only | staff invokes the outbound read | destination is HTTPS, exact-host allowlisted, redirect-free, timed out, and response preview is bounded |
| `User`, `Record`, and `RecordNote` SQLModel rows | only through the rules above | lifecycle seed code may create local fixtures | ownership is `Record.user_id`; notes inherit scope through `RecordNote.record_id` |

Foreign records must be indistinguishable from missing records (`404`). Staff has a deliberate
cross-owner exception only for record notes; staff does not implicitly bypass owner scoping for
record reads, lists, or search.

Anything new that looks up or mutates a resource by a client-supplied identifier is tenant-scoped
until this file declares otherwise. Report a missing policy declaration at medium confidence when
the intended scope cannot be derived.

## Controls that count

- A SQLModel query constrained by `Record.user_id == current_user.id`.
- A post-lookup owner comparison against `current_user.id` before response or mutation.
- `get_current_staff_user`, or a role check against the token-derived current user, for a
  declared staff-wide action.
- Public response models that exclude `hashed_password` and other internal fields.
- The webhook's exact normalized-host allowlist, HTTPS requirement, disabled redirects, fixed
  timeout, and bounded preview.

## Legitimate patterns that are not findings

- `GET <prefix>/me`: there is no client-supplied identity.
- SQLModel expressions and `session.get` are parameterized; their presence alone is not SQL
  injection.
- Local fixture seeding in `app/core/db.py` uses `settings.SEED_PASSWORD` and is disabled outside
  `ENVIRONMENT=local`.
- Local-only exception detail in `app/main.py` is not evidence of production disclosure unless a
  change makes local behavior reachable in staging or production.
- The intentionally public health and API-documentation endpoints listed above.
