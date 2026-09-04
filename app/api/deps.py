"""Authentication, authorization and data-access vocabulary for the API.

Every word a route may use to say who can call it and which rows it may touch is
defined here and nowhere else. ``PolicyRouter`` turns those words into FastAPI
dependencies at import time and refuses to register a route whose declaration is
contradictory or incomplete, so an authorization mistake fails the app at boot
rather than surfacing as a leaked row.

Identity
    ``CurrentUser``  the caller; injected by ``PolicyRouter`` on every route that
                     is not ``PUBLIC``, so a route with no auth in its signature
                     still returns 401.
    ``StaffUser``    the caller, who must hold ``Scope.staff``.

Rows (generic over a model that declares ``__access__``)
    ``Owned[Model]``      one row of ``Model`` owned by the caller; foreign and
                          missing rows are both 404.
    ``AnyOwner[Model]``   one row of ``Model``; the owner always passes, another
                          caller passes only with ``Model.__access__.read_any``,
                          otherwise 404.
    ``OwnedQuery[Model]`` a ``ScopedRows`` pre-filtered to the caller's rows.

Escape hatch
    ``PUBLIC`` in ``dependencies=[...]``: no principal at all. The only route
    marker that may coexist with a ``Session`` parameter.

Routes never receive a ``Session``: the loaders do the querying, so the owner
filter cannot be forgotten or written wrong in a route body.
"""

import inspect
import uuid
from collections.abc import Callable, Generator, Sequence
from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Generic,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

import jwt
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi import params as fastapi_params
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, func, select

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import Access, Scope, TokenPayload, User, UserRole

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login",
    auto_error=False,
    scheme_name="Bearer",
)

# ---------------------------------------------------------------------------
# Session and identity
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def decode_oauth2_token(token: TokenDep) -> TokenPayload:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        return token_data
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    token_data = decode_oauth2_token(token)
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

ROLE_SCOPES: dict[UserRole, frozenset[Scope]] = {
    UserRole.member: frozenset({Scope.records_read}),
    UserRole.staff: frozenset(Scope),
}


def scopes_for(user: User) -> frozenset[Scope]:
    """Scopes granted by the user's role. An unknown role grants nothing."""
    try:
        return ROLE_SCOPES[UserRole(user.role)]
    except ValueError:
        return frozenset()


def _check_scopes(security_scopes: SecurityScopes, current_user: CurrentUser) -> User:
    granted = {scope.value for scope in scopes_for(current_user)}
    if not set(security_scopes.scopes) <= granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


def require(*scopes: Scope) -> Any:
    """Route-level scope requirement for ``dependencies=[require(Scope.x)]``."""
    return Security(_check_scopes, scopes=[scope.value for scope in scopes])


StaffUser = Annotated[User, Security(_check_scopes, scopes=[Scope.staff.value])]


def _anonymous() -> None:
    return None


# Sentinel: ``dependencies=[PUBLIC]`` opts a route out of identity injection.
PUBLIC = Depends(_anonymous)

# ---------------------------------------------------------------------------
# Row access
# ---------------------------------------------------------------------------

M = TypeVar("M", bound=SQLModel)


class PolicyError(TypeError):
    """A route declaration is contradictory or incomplete. Raised at import."""


def access_of(model: type[Any]) -> Access:
    access = getattr(model, "__access__", None)
    if not isinstance(access, Access):
        raise PolicyError(f"{model.__name__} declares no __access__")
    return access


class ScopedRows(Generic[M]):
    """A query over ``model`` that can only ever see the caller's rows.

    Routes narrow it with ``where`` and page it with ``count``/``page``; the
    owner filter is fixed at construction and cannot be removed.
    """

    def __init__(self, session: Session, model: type[M], filters: tuple[Any, ...]):
        self._session = session
        self._model = model
        self._filters = filters

    def where(self, *clauses: Any) -> "ScopedRows[M]":
        return ScopedRows(self._session, self._model, self._filters + clauses)

    def count(self) -> int:
        statement = select(func.count()).select_from(self._model).where(*self._filters)
        return self._session.exec(statement).one()

    def page(self, skip: int, limit: int) -> Sequence[M]:
        statement = select(self._model).where(*self._filters).offset(skip).limit(limit)
        return self._session.exec(statement).all()


@dataclass(frozen=True)
class RowAccess:
    """What a generated loader grants; attached to it as ``__row_access__`` so
    ``app.api.policy`` can read a mounted route's row policy without parsing."""

    marker: str  # "Owned" | "AnyOwner" | "OwnedQuery"
    model: type[Any]
    param: str | None  # path parameter name for single-row loaders

    @property
    def label(self) -> str:
        return f"{self.marker}[{self.model.__name__}]"


@dataclass(frozen=True)
class _RowMarker:
    widen: bool  # False: owner only. True: owner, or anyone holding read_any.


@dataclass(frozen=True)
class _RowsMarker:
    pass


Owned = Annotated[M, _RowMarker(widen=False)]
AnyOwner = Annotated[M, _RowMarker(widen=True)]
OwnedQuery = Annotated[ScopedRows[M], _RowsMarker()]


def _scope_param(scope: str) -> Any:
    return Annotated[User, Security(_check_scopes, scopes=[scope])]


def _row_loader(model: type[Any], marker: _RowMarker, verb: str) -> Callable[..., Any]:
    access = access_of(model)
    if access.owner_field is None:
        raise PolicyError(f"{model.__name__}.__access__ has no owner_field")
    scope = _verb_scope(model, verb)
    if marker.widen and access.read_any is None:
        raise PolicyError(
            f"{model.__name__}.__access__ has no read_any; AnyOwner not allowed"
        )
    owner_field = access.owner_field
    read_any = access.read_any
    row_param = f"{model.__tablename__}_id"

    def load(**kwargs: Any) -> Any:
        session: Session = kwargs["session"]
        current_user: User = kwargs["current_user"]
        row = session.get(model, kwargs[row_param])
        if row is not None and getattr(row, owner_field) != current_user.id:
            widened = marker.widen and read_any in scopes_for(current_user)
            if not widened:
                row = None  # foreign rows are indistinguishable from missing ones
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{model.__name__} not found",
            )
        return row

    kw = inspect.Parameter.KEYWORD_ONLY
    load.__dict__["__signature__"] = inspect.Signature(
        [
            inspect.Parameter("session", kw, annotation=SessionDep),
            inspect.Parameter("current_user", kw, annotation=_scope_param(scope)),
            inspect.Parameter(row_param, kw, annotation=uuid.UUID),
        ],
        return_annotation=model,
    )
    load.__dict__["__row_access__"] = RowAccess(
        marker="AnyOwner" if marker.widen else "Owned", model=model, param=row_param
    )
    return load


def _rows_loader(model: type[Any], verb: str) -> Callable[..., Any]:
    access = access_of(model)
    if access.owner_field is None:
        raise PolicyError(f"{model.__name__}.__access__ has no owner_field")
    scope = _verb_scope(model, verb)
    owner_column = getattr(model, access.owner_field)

    def load(**kwargs: Any) -> Any:
        session: Session = kwargs["session"]
        current_user: User = kwargs["current_user"]
        return ScopedRows(session, model, (owner_column == current_user.id,))

    kw = inspect.Parameter.KEYWORD_ONLY
    load.__dict__["__signature__"] = inspect.Signature(
        [
            inspect.Parameter("session", kw, annotation=SessionDep),
            inspect.Parameter("current_user", kw, annotation=_scope_param(scope)),
        ],
        return_annotation=ScopedRows[model],  # type: ignore[valid-type]
    )
    load.__dict__["__row_access__"] = RowAccess(
        marker="OwnedQuery", model=model, param=None
    )
    return load


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


@dataclass
class _Declaration:
    scopes: set[str]
    public: bool = False
    has_session: bool = False
    has_identity: bool = False
    has_rows: bool = False


def _security_scopes(item: Any) -> set[str] | None:
    if isinstance(item, fastapi_params.Security):
        return set(item.scopes or ())
    return None


def _verb_scope(model: type[Any], verb: str) -> str:
    access = access_of(model)
    scope = access.read if verb == "read" else access.write
    if scope is None:
        raise PolicyError(f"{model.__name__}.__access__ has no {verb} scope")
    return scope.value


def _rewrite_param(annotation: Any, verb: str, decl: _Declaration) -> Any:
    """Return the annotation FastAPI should see, recording what it declares."""
    if get_origin(annotation) is not Annotated:
        if inspect.isclass(annotation) and issubclass(annotation, Session):
            decl.has_session = True
        return annotation

    base, *metadata = get_args(annotation)
    if inspect.isclass(base) and issubclass(base, Session):
        decl.has_session = True

    new_metadata: list[Any] = []
    for item in metadata:
        if isinstance(item, _RowMarker):
            decl.has_rows = True
            decl.scopes.add(_verb_scope(base, verb))
            new_metadata.append(Depends(_row_loader(base, item, verb)))
        elif isinstance(item, _RowsMarker):
            decl.has_rows = True
            (model,) = get_args(base)
            decl.scopes.add(_verb_scope(model, verb))
            new_metadata.append(Depends(_rows_loader(model, verb)))
        else:
            scopes = _security_scopes(item)
            if scopes is not None:
                decl.scopes |= scopes
                decl.has_identity = True
            elif (
                isinstance(item, fastapi_params.Depends)
                and item.dependency is get_current_user
            ):
                decl.has_identity = True
            new_metadata.append(item)
    return Annotated[(base, *new_metadata)]


class PolicyRouter(APIRouter):
    """``APIRouter`` that wires and checks the access-control vocabulary.

    On every ``add_api_route`` it (1) replaces ``Owned``/``AnyOwner``/``OwnedQuery``
    markers with the generated loaders, (2) injects ``CurrentUser`` unless the
    route is ``PUBLIC``, (3) rejects a ``Session`` parameter on a non-public route,
    (4) rejects ``PUBLIC`` combined with any identity or row marker, and
    (5) rejects a ``response_model`` whose ``__access__`` needs a scope the
    route's signature does not grant. Violations raise ``PolicyError`` at import.
    """

    def add_api_route(
        self, path: str, endpoint: Callable[..., Any], **kwargs: Any
    ) -> None:
        methods = set(kwargs.get("methods") or {"GET"})
        verb = "read" if methods <= {"GET", "HEAD"} else "write"
        dependencies = list(kwargs.get("dependencies") or [])
        decl = _Declaration(scopes=set(), public=any(d is PUBLIC for d in dependencies))
        for dep in dependencies:
            scopes = _security_scopes(dep)
            if scopes is not None:
                decl.scopes |= scopes
                decl.has_identity = True

        hints = get_type_hints(endpoint, include_extras=True)
        signature = inspect.signature(endpoint)
        parameters = []
        for name, parameter in signature.parameters.items():
            annotation = _rewrite_param(
                hints.get(name, parameter.annotation), verb, decl
            )
            parameters.append(parameter.replace(annotation=annotation))

        label = f"{'/'.join(sorted(methods))} {self.prefix}{path}"
        if decl.public and (decl.has_identity or decl.has_rows):
            raise PolicyError(f"{label}: PUBLIC route declares identity or row access")
        if decl.has_session and not decl.public:
            raise PolicyError(
                f"{label}: Session is only allowed on PUBLIC routes; use a row loader"
            )

        response_model = kwargs.get("response_model")
        if inspect.isclass(response_model):
            response_access = getattr(response_model, "__access__", None)
            if isinstance(response_access, Access):
                name = response_model.__name__
                if decl.public:
                    raise PolicyError(
                        f"{label}: PUBLIC route returns access-controlled {name}"
                    )
                if response_access.read.value not in decl.scopes:
                    raise PolicyError(
                        f"{label}: response {name} needs {response_access.read.value},"
                        f" signature grants {sorted(decl.scopes) or 'nothing'}"
                    )

        if not decl.public:
            dependencies.insert(0, Depends(get_current_user))
        endpoint.__dict__["__signature__"] = signature.replace(parameters=parameters)
        kwargs["dependencies"] = dependencies
        super().add_api_route(path, endpoint, **kwargs)
