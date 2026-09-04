# Auth model — records-api

Maintained by hand. Reviewers treat this as ground truth for "who may do what"; if the
code disagrees with this file, that disagreement *is* a finding.

## Identity

- `POST /api/login` → HS256 JWT (`app/auth.py: create_access_token`). Claim `sub` = user id.
- `get_current_user` (`../../../../app/core/auth.py`) is the only authentication dependency. Every route
  except `/health` and `/api/login` takes `Annotated[User, Depends(get_current_user)]`.
- FastAPI also serves `/docs`, `/redoc`, `/openapi.json` unauthenticated (framework
  defaults, not in the route map). Known and accepted for a dev service; a reviewer may
  note it at `low`, not higher.
- `User` (`../../../../app/models.py`) carries `id`, `email`, `role`. Roles: `member`, `staff`.
- Known, tracked weaknesses in the identity layer are listed in `baseline.md` (verifier
  only). Reviewers report what they see; the verifier applies the baseline.

## Authorization

There is **no central authorization layer**. Each handler enforces (or fails to enforce) its
own rule. Three styles exist today:

| style | example | acceptable as a control? |
|---|---|---|
| owner check: compares `record["owner_id"]` (or equivalent) to `current_user.id` before returning | `GET /api/records/{id}/notes` | yes |
| role gate: rejects unless `current_user.role == "staff"` | `POST /api/webhooks/vendor-preview` | yes, when the resource is legitimately staff-wide |
| none: authenticated is treated as authorized | `GET /api/records/{id}` | **no** for tenant-scoped resources |

A control only counts if the compared identity comes from `current_user` (token-derived).
Role or id read from the request body, query, or headers is **not** a control.

## Resources and expected scope

| resource / store | tenant-scoped? | who may read | who may write |
|---|---|---|---|
| `db.RECORDS` (records, notes) | yes — keyed by `owner_id` | owner, staff | owner |
| `db.USERS` | yes | self (`/me`) | nobody via API |
| search over records (`/api/search`) | yes — results must be filtered to caller's records or staff | owner, staff | — |
| vendor webhook preview | staff-only action, no per-record scope | staff | staff |

Anything new that looks up by a client-supplied identifier and is not listed here is
**tenant-scoped until someone declares otherwise** — flag it, medium confidence, and say
that the declaration is what's missing.

## Legitimate patterns that are NOT findings

- `GET /api/me` — no client-supplied id; identity comes from the token.
- Lookups keyed only by `current_user.id` (e.g. `RECORDS_BY_OWNER[current_user.id]`).
- A role gate on an action that has no per-tenant resource (webhooks).
- Test fixtures under `../../../../tests/` and `../../../../helpers/` that hardcode credentials for the fake DB.
