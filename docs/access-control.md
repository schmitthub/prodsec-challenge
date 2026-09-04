# Access control: how it works

This document explains the access-control design in `app/api/deps.py` end to end:
what problem it solves, what each piece does, what happens on a request, what
each enforcement layer catches, and how to do day-to-day work with it.

## 1. The problem

"Broken access control" is not "forgot to require a login". It is a logged-in
caller receiving a row, or a capability, they were not entitled to. Two shapes:

- **Object level.** Bob asks for `/records/<alice's id>` and gets it (IDOR).
- **Function level.** A member calls a staff-only endpoint and it works.

Before this change, every route implemented its own control inline:

```python
@router.get("/records/{record_id}", response_model=RecordPublic)
def read_record(session: SessionDep, current_user: CurrentUser, record_id: uuid.UUID):
    record = session.get(Record, record_id)
    if not record or record.user_id != current_user.id:  # the control
        raise HTTPException(status_code=404, detail="Record not found")
    return record
```

The two-line `if` is the security boundary, and it lives in the route body. Every
route that touches a record re-writes it. The notes route had its own variant,
comparing `current_user.role != "staff"` as a raw string. The webhook route used a
third mechanism, `dependencies=[Depends(get_current_staff_user)]`. Three
mechanisms for one concern means:

- a reviewer has to read every body to know whether the check is there and right;
- a linter cannot tell a correct body from a missing check, because "is this
  `if` the right ownership test" is not a pattern-matching question;
- a new contributor copies whichever route they saw first, and drifts.

## 2. The idea

Routes **declare** who may call them and which rows they may touch. They never
**implement** it. The declaration uses a small, fixed vocabulary defined in one
file, `app/api/deps.py`. The policy for a row type is written once, on the type
itself. The router turns declarations into FastAPI dependencies at import time
and refuses to register anything contradictory or incomplete.

The same route today:

```python
@router.get("/records/{record_id}", response_model=RecordPublic)
def read_record(record: Owned[Record]) -> Any:
    return record
```

There is nothing left in the body to get wrong. The lookup, the scope check,
the ownership check and the 404 all happen before the body runs, in code that
exists once.

Because the vocabulary is finite and syntactic, four things become possible that
were not before:

1. the router can validate a declaration at boot;
2. semgrep can check that every route uses the vocabulary and nothing else;
3. a test can read the declared policy back out of the running app and
   snapshot it, so any change is a reviewable diff;
4. a test can derive the *expected* status for every route × caller from the
   declaration alone and compare it with what the server actually does.

## 3. The building blocks

### 3.1 `Scope` and `Access` (in `app/models.py`)

```python
class Scope(StrEnum):
    records_read = "records:read"
    records_read_any = "records:read:any"  # cross-owner read
    webhooks_preview = "webhooks:preview"
    staff = "role:staff"


@dataclass(frozen=True)
class Access:
    read: Scope
    write: Scope | None = None  # None: never written through the API
    owner_field: str | None = None  # column holding the owning user's id
    read_any: Scope | None = None  # None: rows can never be widened past the owner
```

`Scope` is the permission vocabulary. `Access` is attached to a model as
`__access__` and says what it takes to see or change that type:

```python
RECORD_ACCESS = Access(
    read=Scope.records_read, owner_field="user_id", read_any=Scope.records_read_any
)


class RecordBase(SQLModel):
    __access__: ClassVar[Access] = RECORD_ACCESS
    ...
```

`RecordBase` is the parent of `Record` (the table), `RecordCreate` and
`RecordPublic` (the response), so all three share it. `RecordsPublic` and the
note types declare the same object explicitly: a note is visible exactly when its
record is. Scopes are not stored in the JWT; they are derived from the user's
role on each request (§3.2). The token still carries only `sub` and `exp`.

### 3.2 Roles → scopes

```python
ROLE_SCOPES = {
    UserRole.member: frozenset({Scope.records_read}),
    UserRole.staff:  frozenset(Scope),          # everything
}

def scopes_for(user) -> frozenset[Scope]        # unknown role string → empty set

def _check_scopes(security_scopes: SecurityScopes, current_user: CurrentUser) -> User:
    # 403 "The user doesn't have enough privileges" unless every required scope is granted
```

`_check_scopes` is a FastAPI `SecurityScopes` dependency. FastAPI passes it the
union of every `scopes=[...]` declared on the path that led to it, so it does not
matter whether the requirement came from a route decorator, a marker, or
`StaffUser`; they accumulate and are checked once.

Two ways to say a route needs a scope:

```python
require(Scope.webhooks_preview)  # for dependencies=[...] on the decorator
StaffUser  # a User parameter that must hold role:staff
```

### 3.3 Identity and the public opt-out

```python
CurrentUser = Annotated[User, Depends(get_current_user)]  # 401 without a valid token
PUBLIC = Depends(_anonymous)  # no-op sentinel
```

`PolicyRouter` injects `Depends(get_current_user)` into every route it
registers unless the decorator says `dependencies=[PUBLIC]`. So a route whose
signature mentions no user at all still returns 401 without a token. `PUBLIC` is
the only escape hatch and it is a distinct, grep-able word. Today only
`POST /login` uses it.

### 3.4 Row markers

```python
Owned = Annotated[M, _RowMarker(widen=False)]
AnyOwner = Annotated[M, _RowMarker(widen=True)]
OwnedQuery = Annotated[ScopedRows[M], _RowsMarker()]
```

These are generic `Annotated` aliases over a `TypeVar`. `Owned[Record]` is
literally `Annotated[Record, _RowMarker(widen=False)]`. That matters for two
readers:

- **mypy** sees `Record`, so `record.user_id` type-checks and the route
  needs no casts.
- **PolicyRouter** sees the marker object in the metadata and knows to replace
  it with a generated dependency.

The marker cannot build the dependency itself because it never sees `M`.
The router does that, per route, at registration (§3.6).

| Marker | Grants | Foreign row |
|---|---|---|
| `Owned[Model]` | one row where `owner_field == caller.id` | 404 |
| `AnyOwner[Model]` | one row; owner always passes; anyone else passes only with `__access__.read_any` | 404 |
| `OwnedQuery[Model]` | a `ScopedRows` query pre-filtered to the caller's rows | n/a, filtered |

"Widening" is a different word (`Owned` → `AnyOwner`), never a flag. A widened
route shows up in the diff as a type change, and `AnyOwner` on a type whose
`__access__` has no `read_any` is a boot error: what can be widened is
configured on the data, not chosen by the route.

### 3.5 The generated loaders

`_row_loader(model, marker, verb)` builds the function behind `Owned`/`AnyOwner`:

```python
def load(**kwargs):
    session, current_user = kwargs["session"], kwargs["current_user"]
    row = session.get(model, kwargs[row_param])
    if row is not None and getattr(row, owner_field) != current_user.id:
        if not (marker.widen and read_any in scopes_for(current_user)):
            row = None  # foreign == missing
    if row is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return row
```

Its signature is synthesised, because FastAPI resolves dependencies from
signatures:

```
(session: SessionDep,
 current_user: Annotated[User, Security(_check_scopes, scopes=[<read or write scope>])],
 record_id: uuid.UUID)
```

The path parameter is named `<tablename>_id`, so `Owned[Record]` binds
`{record_id}` in the path with no configuration. The `Security(...)` annotation
on `current_user` is what makes the scope check run before the lookup.

`_rows_loader(model, verb)` builds the `OwnedQuery` dependency. It returns

```python
ScopedRows(session, model, (owner_column == current_user.id,))
```

`ScopedRows` exposes `where(*clauses)`, `count()` and `page(skip, limit)`. The
owner filter is set at construction and there is no method to remove it; the
search route adds its substring match on top and cannot widen.

Both loaders carry a `__row_access__` tag (`RowAccess(marker, model, param)`)
so the policy walker (§7) can read what a mounted route grants without
re-parsing anything.

### 3.6 `PolicyRouter`

Every route module does `router = PolicyRouter(tags=[...])` instead of
`APIRouter`. `PolicyRouter.add_api_route` runs when the decorator is applied,
i.e. at import, and does this in order:

1. Works out the **verb** from the HTTP methods: `GET`/`HEAD` → `read`, anything
   else → `write`. A write route on a type with no `write` scope is a
   `PolicyError`.
2. Reads `dependencies=[...]` on the decorator, noting `PUBLIC` and any
   `Security(...)` scopes (from `require`).
3. Walks the signature with `get_type_hints(include_extras=True)`. For each
   parameter:
   - a `_RowMarker` → builds the loader, records the model's read/write scope,
     replaces the annotation with `Annotated[Model, Depends(loader)]`;
   - a `_RowsMarker` → same with `_rows_loader`;
   - a `Security(...)` → records its scopes and that identity is present;
   - `Depends(get_current_user)` (i.e. `CurrentUser`) → identity present;
   - a `Session` / `SessionDep` → records that the route wants a session.
4. Rejects, with `PolicyError`:
   - `Session` on a route that is not `PUBLIC`;
   - `PUBLIC` together with any identity or row marker;
   - `PUBLIC` with a `response_model` that has `__access__`;
   - a `response_model` whose `__access__.read` scope is not among the scopes
     the signature grants (the route says `records:read` but returns a type
     that needs something else: misattribution);
   - a marker on a type without `__access__`, without `owner_field`, or
     `AnyOwner` without `read_any`.
5. If not `PUBLIC`, prepends `Depends(get_current_user)` to the route's
   dependencies.
6. Writes the rewritten signature onto the endpoint (`__signature__`) and calls
   the real `APIRouter.add_api_route`.

The result is a normal FastAPI route. Nothing custom runs per request; the
router only does the wiring once. `Security(scopes=...)` also puts the scopes
into the OpenAPI document, which is what the policy walker and the older
OpenAPI-driven authz test read.

## 4. A request, step by step

**Bob asks for Alice's record.** `GET /api/v1/records/<alice-record-id>` with
Bob's bearer token. The route is `read_record(record: Owned[Record])`.

1. `get_current_user` (injected by the router): decode the token → load Bob.
   No token → 401. Bad token → 403.
2. The loader's `current_user` parameter is `Security(_check_scopes,
   scopes=["records:read"])`. Bob is a member, members hold `records:read`.
   Passes. (A caller without the scope stops here with 403.)
3. The loader runs: `session.get(Record, id)` finds Alice's row.
   `row.user_id != bob.id`, the marker is `Owned` (no widening), so `row = None`
   → 404 "Record not found". Exactly what a missing id returns.

**Staff asks for Alice's record's notes.** Route is
`read_record_notes(record: AnyOwner[Record])`.

1. Token → clinician user.
2. Scope check: staff hold every scope. Passes.
3. Loader: row found, owner differs, marker is `AnyOwner`, and
   `records:read:any` is in staff scopes → widened, row returned. Body builds
   `RecordNotesPublic`.

**Staff asks for Alice's record itself.** Route is `Owned[Record]`, not
`AnyOwner`. Step 3 sets `row = None` → 404. Staff can read any record's notes
but not the record body, which is today's declared policy; if that is wrong,
the fix is one word in the route (`Owned` → `AnyOwner`) and it shows up in the
policy snapshot diff.

**Member calls the webhook preview.** Decorator has
`dependencies=[require(Scope.webhooks_preview)]`. Token → member. Scope check:
members do not hold `webhooks:preview` → 403 before the body is even parsed.

## 5. Why routes cannot hold a `Session`

The loaders are only a guarantee if they are the *only* way rows enter a route.
If a route can also take `session: SessionDep`, then `session.get(Record, id)`
followed by `return record` is legal again and the ownership check is back to
being something a reviewer must look for in bodies.

So a `Session` parameter on a non-`PUBLIC` route is refused at boot by
`PolicyRouter`, and at commit by the semgrep rule `fastapi-route-session-param`.
A route that needs a query the existing loaders don't express gets a new loader
in `deps.py`, reviewed once, instead of inline SQL. That friction is the point.

The router only sees signatures, so opening a session inside a body
(`Session(engine)`, importing `engine` or `get_db`) is the way around it. The
semgrep rule `fastapi-route-opens-session` refuses any of those names in a route
module, and the taint rule catches `session.get`/`select` results reaching a
response.

`POST /login` is `PUBLIC` and takes a session, because it has no caller yet and
must look the user up by email. It is the only such route, and the walker test
requires it to be listed with a reason.

## 6. Enforcement layers

| Layer | When it runs | What it catches |
|---|---|---|
| `PolicyRouter` | app import | contradictory or incomplete declarations; response type needing an ungranted scope; `Session` on an authenticated route; forgotten auth (identity is injected, so it cannot be forgotten) |
| Loaders | per request | wrong owner, wrong scope, widening without `read_any` |
| Semgrep (`.semgrep/fastapi-access-control.yaml`) | pre-commit, CI | routes not using the vocabulary: `APIRouter`, `Session`, bare table models, foreign `dependencies=`, inline `.role` checks, 403 in a route, direct DB access, taint to a response |
| `tests/api/test_policy_router.py` | pytest | each `PolicyError` branch and the default 401 |
| `tests/api/test_route_policy.py` | pytest | exactly one policy per mounted route; `PUBLIC` routes allowlisted with a reason; snapshot equals `app/api/policy.json` |
| `tests/api/test_access_matrix.py` | pytest | observed status matches declared policy for every route × caller |
| `tests/api/test_authz_invariant.py` | pytest | (pre-existing) no member ever receives another user's identifiers on any GET |

Semgrep is the fast feedback; the router and the tests are the guarantee.
Semgrep rules are deliberately **shape** checks. They never try to understand
what a dependency does. `dependencies=[Depends(get_current_staff_user)]` was
refused not because semgrep judged the function, but because the only two
things allowed in that list are `require(...)` and `PUBLIC`.

## 7. Semgrep rules

All in `.semgrep/fastapi-access-control.yaml`, scoped by `paths` to
`app/api/routes/` (two apply to all of `app/`).

| Rule | Severity | Matches |
|---|---|---|
| `fastapi-router-not-policy-router` | ERROR | `APIRouter(...)` in a route module |
| `fastapi-route-session-param` | ERROR | `Session`/`SessionDep` parameter on a route not marked `PUBLIC` |
| `fastapi-route-opens-session` | ERROR | `Session(...)`, `engine` or `get_db` anywhere in a route module |
| `fastapi-route-model-param-unwrapped` | ERROR | a parameter typed `Record`/`RecordNote`/`User` (or `Annotated[...]` of one) without a marker |
| `fastapi-route-foreign-dependency` | ERROR | anything in `dependencies=[...]` that is not `require(...)` or `PUBLIC` |
| `fastapi-require-string-scope` | ERROR | `require("...")` with a string instead of a `Scope` member |
| `fastapi-inline-role-check` | ERROR | `x.role ==` / `!=` / `in` anywhere in `app/` except `deps.py` |
| `fastapi-route-raises-403` | ERROR | `HTTPException(403 ...)` in a route |
| `fastapi-route-raw-row-to-response` | ERROR, taint | `session.get(Model)` / `select(...)` / `session.exec(...)` flowing to `return` or `*Public(data=...)` inside a route |
| `fastapi-route-path-model-mismatch` | WARNING | a `/records...` path whose marker loads a non-`Record` model |
| `fastapi-escape-hatch` | WARNING | any `PUBLIC` route; advisory, never blocking, never silent |

The sibling file `.semgrep/fastapi-access-control.py` is a fixture: comments
mark each statement as an expected finding or an expected non-finding. The
semgrep prek hook runs `semgrep --test` on it before every local scan (via
`.github/scripts/semgrep_gate.py`), so a rule edit that stops matching, or
starts matching an `ok` case, fails the commit. The gate blocks on
ERROR/HIGH/CRITICAL only; WARNINGs annotate.

## 8. Reading the policy back: walker, snapshot, matrix

`app/api/policy.py` walks the mounted app and, for every route, collects: is it
`PUBLIC`, does it carry identity, which OAuth scopes it requires, and which
`RowAccess` tags its loaders carry. FastAPI 0.141 includes routers lazily, so
the walk goes through the private `_IncludedRouter.effective_candidates()`
tree; a test guards that API.

`app/api/policy.json` is a checked-in dump of that table:

```json
"GET /api/v1/records/{record_id}/notes": {
  "scopes": ["records:read"],
  "rows": ["AnyOwner[Record]"]
},
"POST /api/v1/login": "PUBLIC"
```

`test_policy_snapshot_matches` fails on any difference and names the
regeneration command (`uv run python -m app.api.policy`). The effect: a change
to who can reach what is a JSON diff in the PR, reviewable without reading route
code.

`test_access_matrix.py` takes the same table and, for each route × caller in
{anonymous, owner, other member, staff}, derives the expected outcome purely
from the declaration:

1. `PUBLIC` → granted.
2. no caller → 401.
3. route scopes not a subset of `scopes_for(caller)` → 403.
4. for each single-row loader where caller is not the owner: `Owned` → 404;
   `AnyOwner` → granted only if `read_any` is in the caller's scopes, else 404.
5. otherwise granted (any status outside 401/403/404, so 422 for a route that
   needed a body we did not send).

Then it makes the request and asserts agreement. Disabling the ownership line in
the loader made exactly the three cross-owner cases fail; nothing else moved.
That is the test that catches an implementation that grants more or less than it
declares, which neither the router nor semgrep can see.

## 9. Day-to-day

**Add a read route for an existing model.**

```python
@router.get("/records/{record_id}/summary", response_model=RecordPublic)
def read_summary(record: Owned[Record]) -> Any: ...
```

Then `uv run python -m app.api.policy` and commit the JSON diff. The matrix test
covers it automatically.

**Let staff see it across owners.** Change `Owned` to `AnyOwner`. The snapshot
diff shows `"rows": ["AnyOwner[Record]"]`; the matrix now expects staff to be
granted and members 404.

**Add a staff-only action with no rows.**

```python
@router.post("/exports", dependencies=[require(Scope.exports_run)])
```

Add `exports_run` to `Scope`; staff already hold everything, members nothing new.

**Add a write route.** Give the model's `Access` a `write` scope first; a
`PATCH` with `Owned[Record]` on a type without one is a boot error.

**Add a new table.** Declare `__access__` on its base class, and add its name to
the table-model regex in the two semgrep rules that list models
(`fastapi-route-model-param-unwrapped`, `fastapi-route-raw-row-to-response`).
Give `tests/api/test_access_matrix.py::owner_rows` a fixture row for it.

**Add an unauthenticated route.** `dependencies=[PUBLIC]`, no user, no markers,
no access-controlled response type, and add it to `PUBLIC_ROUTES` in
`tests/api/test_route_policy.py` with the reason. Semgrep will WARN on it every
scan; that is intended.

**Need a query the loaders can't express.** Add a loader in `deps.py` next to
the existing ones, tag it with `__row_access__`, and use it from the route. Do
not add a `Session` parameter.

## 10. Limits, stated plainly

- The walker relies on a private FastAPI API (`_IncludedRouter`). The version is
  pinned in `uv.lock`; `test_walker_sees_the_api` fails loudly if it moves.
- The table-model list in two semgrep rules is a hardcoded regex.
- "Granted" in the matrix is any status outside 401/403/404, so a 422 counts.
  It proves access control was passed, not that the body was valid.
- The matrix fills path parameters only for `Record`; a new row-loaded model
  fails until `owner_rows` learns it.
- Semgrep refuses wrappers by shape, not by understanding them. A wrapper that
  is genuinely correct still has to be expressed as `require(...)` or a loader.
- Field-level access (hiding some columns from some callers) is not modelled.
  `__access__` is per type. The same machinery would carry it later.
- Row-level security in Postgres was considered and dropped: it is a
  database-tier control, needs a second DB login because superusers bypass it,
  and would guard a path that no longer exists once routes cannot hold a session.

## 11. Files

| File | Role |
|---|---|
| `app/models.py` | `Scope`, `Access`, `__access__` on record and note types |
| `app/api/deps.py` | the whole vocabulary: identity, scopes, markers, loaders, `PolicyRouter` |
| `app/api/policy.py`, `policy.json` | walker and snapshot |
| `app/api/routes/*.py` | declarations only |
| `.semgrep/fastapi-access-control.yaml`, `.py` | rules and fixture |
| `.github/scripts/semgrep_gate.py` | runs fixtures, then scans, then gates |
| `tests/api/test_policy_router.py` | boot-time guarantees |
| `tests/api/test_route_policy.py` | walker invariants and snapshot |
| `tests/api/test_access_matrix.py` | declared vs observed |
