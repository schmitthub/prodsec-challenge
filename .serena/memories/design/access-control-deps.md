# Design: type-bound access control deps (proposal, not implemented)

Status: design agreed in conversation 2026-09-04, nothing built. Branch at the time: `refactor/for-funsies`.
Goal: make broken access control (wrong owner scope, wrong role, wrong data type on a route) structurally
hard and mechanically detectable, not just "missing auth". Lint (semgrep) is fast feedback on a
convention; the guarantees come from the router, the loaders and the DB.

## Problem in today's code

Auth is expressed three ways, so no rule can say "route lacks the required policy":

- `read_me`, `list_my_records`, `search_records`: `current_user: CurrentUser` param (identity only, no role info).
- `preview_vendor_webhook`: `dependencies=[Depends(get_current_staff_user)]`.
- `read_record_notes`: inline `current_user.role != "staff"` (raw string, not `UserRole`).
- `RecordDep` in `app/api/deps.py` is a stale alias of the token dep (named as record lookup, never used).
  Ownership checks live inline in `read_record` / `read_record_notes` (IDOR surface semgrep cannot see).
- Routes take `SessionDep` and query tables directly.

Semgrep is syntactic: it cannot prove `get_current_staff_user` enforces anything or see through a wrapper.
So the contract must be syntactic: a finite vocabulary of names defined in one file.

## Prior art the design borrows from

- Default-deny + explicit opt-out: Django 5.1 `LoginRequiredMiddleware`/`@login_not_required`, DRF
  `DEFAULT_PERMISSION_CLASSES`, Rails `before_action :authenticate_user!`/`skip_before_action`, Spring
  `anyRequest().authenticated()`/`permitAll()`, ASP.NET `FallbackPolicy`/`[AllowAnonymous]`, NestJS global
  `APP_GUARD` + `@Public()`, Istio/OPA default-deny at ingress.
- "Did you authorize?" tripwire: Pundit `verify_authorized` / `verify_policy_scoped`, CanCanCan
  `check_authorization`, GitLab every-endpoint metadata specs, Spectral `operation-security-defined`.
- Policy bound to data, not routes: Pundit `policy_scope`, Oso `authorized_query`, django-guardian
  `get_objects_for_user`, Postgres RLS (Hasura/PostgREST/Supabase).
- Types as capabilities: "parse, don't validate", Rocket/Axum request guards.
- This repo descends from full-stack-fastapi-template (per-route deps only, no default-deny). That is the gap.

## Design

### 1. Policy bound to the type

Every table model and every `*Public` response model declares what it takes to see/modify it:

```python
class Record(SQLModel, table=True):
    __access__ = Access(
        read=Scope.records_read,
        write=Scope.records_write,
        owner_field="user_id",  # rows scoped to caller by default
        read_any=Scope.records_read_any,  # cross-owner widening; absent = cannot widen
        public_read=False,  # anonymous read; absent = never
    )


class RecordNotesPublic(SQLModel):
    __access__ = Access(read=Scope.notes_read, read_any=Scope.notes_read_any)
```

`Scope` is a `StrEnum` (3.11+). `ROLE_SCOPES: dict[UserRole, frozenset[Scope]]` maps role -> granted scopes.
Scopes derive from `user.role` at request time; JWT stays `sub` + `exp`, `create_access_token`/login untouched.

### 2. Vocabulary (all defined in `app/api/deps.py`, nowhere else)

```python
CurrentUser = Annotated[
    User, Depends(get_current_user)
]  # injected by router by default
StaffUser = Annotated[User, Security(get_current_user, scopes=["role:staff"])]
Owned[
    Model
]  # rows where Model.__access__.owner_field == caller.id; 404 for foreign rows
AnyOwner[
    Model
]  # no owner filter; requires Model.__access__.read_any (=> staff); boot error if type lacks it
OwnedQuery[Model]  # pre-filtered select(); route adds only q/offset/limit
```

Escape hatches, narrowest first. Each is a distinct grep-able word:

| Marker | Means | Router does | Constraints |
|---|---|---|---|
| `OptionalUser` | anonymous or logged in | parse token if present, no 401 | `Owned` 404s when anonymous |
| `Public` | no principal | skip identity injection | `Public` + `Owned[X]` = boot error; login uses this |
| `PublicRows[Model]` | anonymous read of a model | loader with no caller | only if `__access__.public_read` |
| `ServicePrincipal` / `SignedWebhook` | non-user identity (HMAC, API key, mTLS) | verifies that scheme | `Owned` meaningless => boot error |
| `Unscoped[Model]` + `RawSession` | explicit bypass | injects raw session | requires `reason=`; semgrep WARNING; in policy snapshot |

Identity is a sum type `Principal = User | Service | Anonymous`; loaders are written against `Principal`.
"Unauthenticated" is a principal with an empty grant set, not the absence of a check.

`get_current_staff_user` and every inline `.role` comparison are deleted so there is one way.
Routes take no `SessionDep`: a route with no session cannot query; data enters only through typed loaders.
`/health` lives on `app`, outside the router, out of scope.

### 3. Composition semantics

- Params AND together; every dep enforces its own check. `(user: StaffUser, record: Owned[Record])` = staff and own row.
- Widening is a different marker (`Owned` -> `AnyOwner`), never a flag. Shows in the diff as a type change.
- What can widen is configured on the type (`read_any`, `public_read`), so config lives with the data.
- HTTP method picks the verb: GET/HEAD -> `read`, others -> `write`. `Owned[Record]` on PATCH needs `records:write`.
- `Security(scopes=)` accumulates through `SecurityScopes`, so scopes surface in OpenAPI per operation.

### 4. `PolicyRouter(APIRouter)` = wiring + enforcement point

mypy problem: `Owned[Record]` must read as `Record`. On 3.11, `Owned = Annotated[T, _Owner()]` (generic
Annotated alias) gives that, but the marker cannot see `T`. So the router does it in `api_route`:

1. Walk the signature; for `Annotated[Model, _Owner()]` etc. rewrite the default to `Depends(owned(Model))`.
2. Inject `CurrentUser` unless `Public`/`OptionalUser`/`ServicePrincipal` present (FastAPI's
   `APIRouter(dependencies=)` cannot be removed per route, hence injection instead of declaration).
3. Cross-check: union of scopes from all markers + `StaffUser` + `response_model.__access__` + body model on
   writes must be consistent (equal, not subset) with any explicit `require(...)`. Mismatch -> app fails to boot
   with "route declares X, response type needs Y". Pundit's `verify_authorized`, moved to import time.
4. Contradictions (`Public` + `Owned`, `AnyOwner` on a type without `read_any`) -> boot error.

An explicit `require(Scope...)` on the decorator is optional redundancy (checksum) that keeps intent reviewable.

### 5. Postgres row-level security (bottom layer, second phase)

```sql
ALTER TABLE record ENABLE ROW LEVEL SECURITY;
ALTER TABLE record FORCE ROW LEVEL SECURITY;
CREATE POLICY record_owner ON record USING (
  user_id = current_setting('app.user_id', true)::uuid
  OR current_setting('app.role', true) = 'staff'
);
```

`get_db` runs `SET LOCAL app.user_id/app.role` per request. Survives contributors who never read deps.py:
a raw query for a foreign row returns nothing, 404 falls out. Costs: app role must not own tables (or `FORCE`),
migrations run as owner, seeding needs a bypass role. Postgres 17 already in compose and CI.

### 6. Semgrep, `.semgrep/fastapi-access-control.yaml`

Wire `--config=.semgrep/fastapi-access-control.yaml` into BOTH `.pre-commit-config.yaml` and
`.github/workflows/security.yml` (lists must stay in sync). Sibling `.py` fixture with `# ruleid:` / `# ok:`
for `semgrep --test`. Rules are shape checks; none tries to understand what a dep does.

| id | sev | catches |
|---|---|---|
| route-model-param-unwrapped | ERROR | table model in a `@router` signature not wrapped in `Owned`/`AnyOwner`/`OwnedQuery`/`PublicRows`/`Unscoped` |
| route-uses-session | ERROR | `SessionDep`/`Session` in a `@router` signature without `RawSession` |
| route-inline-role-check | ERROR | `.role` comparison outside deps.py |
| route-foreign-dependency | ERROR | anything in `dependencies=` that is not a deps.py marker (wrappers, `Depends(x)`, aliases). Allowlist of names, resolved via `app.api.deps.*` so shadowing/foreign imports fail to match |
| route-raises-403 | ERROR | `HTTPException(403` in routes; only deps.py may 403 (foreign == missing must stay 404) |
| route-path-scope-mismatch | WARNING | `/records...` path with a non-`Record` model marker, etc. |
| taint: raw-row-to-response | ERROR | sources `session.get($M, ...)`, `select($M)` for table models; sanitizers `owned(...)`, `owned_query(...)`; sinks `return $X` in a route, `*Public(data=$X)`. Intraprocedural is enough |
| escape-hatch-used | WARNING | `Public`, `PublicRows`, `Unscoped`, `RawSession` — never silent, never blocking; reason string echoed in message |

### 7. Tests

- Enumerate-all-routes test over `app.routes`: every `APIRoute` under `API_V1_STR` resolves to exactly one
  policy; escape hatches must appear in an explicit allowlist dict (same shape as `EXEMPT_ROUTES` in
  `tests/api/test_authz_invariant.py`), e.g. `{"/login": "OAuth2 token endpoint"}`.
- Policy snapshot: dump `{METHOD path: scopes | PUBLIC | ...}` and assert equal to a checked-in JSON
  (`app/api/policy.json` or under `tests/`, undecided). Policy changes show in the PR diff; catches dynamic routes semgrep cannot see.
- Generated matrix test: for every route x principal (anonymous, member, other member, staff, service), expected
  status derives from `ROLE_SCOPES` + `__access__` (401 unauth, 403 missing scope, 404 foreign row, 2xx own).
  Broken access control = diff between declared table and observed behaviour. Extends the existing OpenAPI walker.
- `CODEOWNERS` on `app/api/deps.py` and the snapshot.

### What each layer catches

| Mistake | Caught by |
|---|---|
| forgot auth | router injects `CurrentUser` by default |
| fetched a row directly | no `SessionDep` in routes; taint rule |
| owner filter wrong | impossible; loader derives it from `__access__` |
| widened without staff | `AnyOwner` loader requires `read_any` |
| response leaks a wider type | router cross-check of `response_model.__access__` |
| wrong model on the route | path<->type rule + matrix test |
| any code path at all | RLS |
| bypass | still possible, never quiet: distinct word, WARNING, snapshot diff, allowlist entry, CODEOWNERS |

## Suggested order

1. `__access__` + `Owned`/`AnyOwner`/`OwnedQuery` loaders + `PolicyRouter` cross-check; convert the four route
   files; delete `get_current_staff_user`, inline role checks, stale `RecordDep`, `SessionDep` from routes.
2. Semgrep rule file + fixture, wired into prek and CI.
3. Route walker + policy snapshot + matrix test.
4. RLS migration + `SET LOCAL` in `get_db`.
5. Escape hatches beyond `Public` only when a caller needs them (vocabulary reserved, not implemented).

## Open decisions

- Snapshot file location.
- Keep explicit `require(...)` on decorators as a redundancy checksum, or infer scopes purely from types.
- RLS in the same PR or a follow-up (recommend follow-up).

Related: `mem:conventions`, `mem:core`.
