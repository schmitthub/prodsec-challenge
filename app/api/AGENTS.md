# `app/api/`

## Directory summary

Shared FastAPI API wiring. This package owns request-scoped database and authentication dependencies plus the aggregate versioned router; concrete endpoint handlers live in `routes/` and have their own guide.

## Role in the project

`app.main` mounts `main.api_router` under `settings.API_V1_STR`. The router includes every endpoint module. `deps.py` is the single source of every access-control word a route may use. Route modules build their router with `PolicyRouter`, which at import rewrites the typed row markers into dependencies, injects `CurrentUser` on every route that is not `PUBLIC`, and raises `PolicyError` for contradictory declarations. Routes never receive a `Session`; row loaders derive the owner filter and required scope from the model's `__access__`. Identity chain: `CurrentUser` -> `get_current_user` -> `SessionDep` + `TokenDep`; scope checks: `_check_scopes` against `ROLE_SCOPES`.

## Child directories

- `routes/` — login, records, search, and webhook endpoint modules; see `routes/AGENTS.md`.

## Files and symbols

### `__init__.py`

Package marker; it defines no code symbols.

### `main.py`

Composes the endpoint routers exposed by the application.

- `api_router`: Aggregate `APIRouter` that includes, in order, `login.router`, `records.router`, `search.router`, and `webhooks.router`.

### `policy.py`

Reads the declared access policy back from the mounted app so tests can check it and diff it.

- `SNAPSHOT`: Path of `policy.json` next to this module.
- `RoutePolicy`: Frozen record of one `METHOD path`: `public`, `identity`, sorted `scopes`, and the `RowAccess` tuple its loaders grant. `key` is `"METHOD path"`; `as_json()` is `"PUBLIC"` or `{"scopes": [...], "rows": ["Owned[Record]", ...]}`.
- `effective_routes(app)`: Yields `(method, path, dependant)` for every mounted route. Walks FastAPI 0.140+'s lazy `_IncludedRouter.effective_candidates()` tree (private API; pinned by `uv.lock`, guarded by `tests/api/test_route_policy.py`).
- `_collect(dependant, scopes, rows, flags)`: Recursive dependency-tree walk marking `public` (`_anonymous`), `identity` (`get_current_user`), OAuth scopes, and `__row_access__` tags.
- `route_policy(method, path, dependant)`: Builds one `RoutePolicy`.
- `route_policies(app)`: All routes, sorted by key. `api_policies(app)`: only those under `settings.API_V1_STR`.
- `policy_table(app)`: `{key: as_json()}` for the API routes; what `policy.json` stores.
- `main()`: `python -m app.api.policy` rewrites `policy.json`. Run it after an intentional policy change; the snapshot test fails until you do.

### `policy.json`

Checked-in snapshot of `policy_table(app)`. A policy change shows up here in the PR diff. Regenerate with `uv run python -m app.api.policy`; never hand-edit.

### `deps.py`

Defines the API's access-control vocabulary: session and identity dependencies, the role→scope table, typed row loaders, the public opt-out, and the router that enforces them.

Session and identity:

- `reusable_oauth2`: `OAuth2PasswordBearer` configured for the versioned `/login` token URL and the `Bearer` scheme name. `auto_error=False` lets a missing credential reach `decode_oauth2_token` so this module emits the intended 401 response.
- `get_db()`: Generator dependency that opens a SQLModel `Session` on the shared engine, yields it for dependency resolution, and closes it when the request dependency scope exits.
- `SessionDep`: Annotated `Session` dependency backed by `get_db`. Allowed in route signatures only on `PUBLIC` routes; everywhere else the loaders own the session.
- `TokenDep`: Annotated bearer-token `str` dependency backed by `reusable_oauth2`. At runtime it can receive `None` because the OAuth2 dependency has `auto_error=False`; `decode_oauth2_token` owns that case.
- `decode_oauth2_token(token)`: Requires a token, decodes it with `settings.SECRET_KEY` while allowing only `security.ALGORITHM`, and validates the decoded mapping as `TokenPayload`. A missing token raises 401 with `WWW-Authenticate: Bearer`; JWT decoding failures (including expiry) or payload-model validation failures raise 403.
- `get_current_user(session, token)`: Decodes the bearer token, loads `User` by the payload's `sub` primary key, and raises 404 when that user no longer exists.
- `CurrentUser`: Annotated `User` dependency backed by `get_current_user`.

Scopes:

- `ROLE_SCOPES`: `UserRole` → `frozenset[Scope]`. Members hold `records:read`; staff hold every scope.
- `scopes_for(user)`: Scopes granted by the user's role; an unknown role string grants nothing.
- `_check_scopes(security_scopes, current_user)`: `SecurityScopes` dependency; raises 403 `The user doesn't have enough privileges` unless every required scope is granted.
- `require(*scopes)`: `Security(_check_scopes, scopes=...)` for `dependencies=[require(Scope.x)]` on a decorator.
- `StaffUser`: Annotated `User` that must hold `Scope.staff`.
- `_anonymous()` / `PUBLIC`: No-op dependency sentinel; `dependencies=[PUBLIC]` opts a route out of identity injection.

Row access:

- `M`: `TypeVar` bound to `SQLModel` for the generic markers.
- `PolicyError`: `TypeError` raised at import for contradictory or incomplete route declarations.
- `access_of(model)`: Returns the model's `Access` or raises `PolicyError` when `__access__` is missing.
- `ScopedRows[M]`: Query object bound to a session, model, and fixed filter tuple. `where(*clauses)` returns a narrower copy, `count()` and `page(skip, limit)` execute; the owner filter set at construction cannot be removed.
- `RowAccess(marker, model, param)`: What a generated loader grants (`Owned`/`AnyOwner`/`OwnedQuery`, the model, the path parameter for single-row loaders). Attached to each loader as `__row_access__` for `policy.py`; `label` renders `Owned[Record]`.
- `_RowMarker(widen)` / `_RowsMarker`: Annotated metadata recognised by `PolicyRouter`.
- `Owned[M]`: One row owned by the caller; foreign and missing rows are both 404.
- `AnyOwner[M]`: One row; the owner always passes, another caller passes only when holding `__access__.read_any`, otherwise 404. Using it on a type without `read_any` is a `PolicyError`.
- `OwnedQuery[M]`: A `ScopedRows[M]` pre-filtered to the caller's rows.
- `_scope_param(scope)`: Builds the `Security`-annotated user parameter loaders use for their scope check.
- `_verb_scope(model, verb)`: `read` or `write` scope from `__access__`; `PolicyError` when the verb has none.
- `_row_loader(model, marker, verb)`: Builds the dependency behind `Owned`/`AnyOwner`. Its signature is generated (`session`, scope-checked `current_user`, `<tablename>_id: UUID`) so the path parameter name follows the model. Loads by primary key and applies the owner/widen rule.
- `_rows_loader(model, verb)`: Builds the dependency behind `OwnedQuery`; returns `ScopedRows` filtered on `__access__.owner_field == current_user.id`. Both loaders carry a `__row_access__` tag.

Router:

- `_Declaration`: What a route's signature and `dependencies=` declare: scopes, public, session, identity, rows.
- `_security_scopes(item)`: Scopes carried by a `Security` dependency, else `None`.
- `_rewrite_param(annotation, verb, decl)`: Returns the annotation FastAPI should see, replacing markers with generated `Depends` and recording scopes, identity, and session use.
- `PolicyRouter`: `APIRouter` whose `add_api_route` rewrites markers, injects `Depends(get_current_user)` unless `PUBLIC`, rejects `Session` on non-public routes, rejects `PUBLIC` combined with identity or row markers, and rejects a `response_model` whose `__access__.read` scope the signature does not grant. Every route module must use it instead of `APIRouter`.
