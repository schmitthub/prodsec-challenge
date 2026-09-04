"""``PolicyRouter`` refuses contradictory or incomplete route declarations at import,
and injects identity on every route that is not ``PUBLIC``.

These tests build throwaway routers; nothing here touches the database.
"""

from typing import Any, ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.api.deps import (
    PUBLIC,
    AnyOwner,
    CurrentUser,
    Owned,
    PolicyError,
    PolicyRouter,
    SessionDep,
    scopes_for,
)
from app.models import Access, Record, RecordPublic, Scope, User


class Orphan(SQLModel):
    """No ``__access__`` at all."""

    id: int


class Unowned(SQLModel):
    __access__: ClassVar[Access] = Access(read=Scope.records_read)
    id: int


class NeverWidened(SQLModel):
    __access__: ClassVar[Access] = Access(
        read=Scope.records_read, owner_field="user_id"
    )
    id: int


def test_route_with_no_identity_in_signature_still_requires_auth() -> None:
    router = PolicyRouter()

    @router.get("/ping")
    def ping() -> dict[str, str]:
        return {"pong": "yes"}

    app = FastAPI()
    app.include_router(router)
    r = TestClient(app).get("/ping")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_public_route_skips_identity() -> None:
    router = PolicyRouter()

    @router.get("/ping", dependencies=[PUBLIC])
    def ping() -> dict[str, str]:
        return {"pong": "yes"}

    app = FastAPI()
    app.include_router(router)
    assert TestClient(app).get("/ping").status_code == 200


def test_session_is_rejected_on_authenticated_routes() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="Session is only allowed on PUBLIC"):

        @router.get("/leak")
        def leak(session: SessionDep) -> Any:
            return session


def test_session_is_allowed_on_public_routes() -> None:
    router = PolicyRouter()

    @router.post("/login", dependencies=[PUBLIC])
    def login(session: SessionDep) -> Any:
        return session


@pytest.mark.parametrize("annotation", [CurrentUser, Owned[Record]])
def test_public_cannot_combine_with_identity_or_rows(annotation: Any) -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="PUBLIC route declares"):

        @router.get("/x/{record_id}", dependencies=[PUBLIC])
        def x(item: annotation) -> Any:  # type: ignore[valid-type]
            return item


def test_public_cannot_return_access_controlled_type() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="access-controlled RecordPublic"):

        @router.get("/x", dependencies=[PUBLIC], response_model=RecordPublic)
        def x() -> Any:
            return None


def test_response_type_needs_scope_the_signature_grants() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="RecordPublic needs records:read"):

        @router.get("/x", response_model=RecordPublic)
        def x(current_user: CurrentUser) -> Any:
            return current_user


def test_row_markers_require_access_declaration() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="Orphan declares no __access__"):

        @router.get("/x/{orphan_id}")
        def x(item: Owned[Orphan]) -> Any:
            return item


def test_owned_requires_owner_field() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="has no owner_field"):

        @router.get("/x/{unowned_id}")
        def x(item: Owned[Unowned]) -> Any:
            return item


def test_any_owner_requires_read_any_on_the_type() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="has no read_any"):

        @router.get("/x/{neverwidened_id}")
        def x(item: AnyOwner[NeverWidened]) -> Any:
            return item


def test_write_methods_need_a_write_scope() -> None:
    router = PolicyRouter()
    with pytest.raises(PolicyError, match="Record.__access__ has no write scope"):

        @router.post("/x/{record_id}")
        def x(item: Owned[Record]) -> Any:
            return item


def test_unknown_role_grants_no_scopes() -> None:
    ghost = User(email="ghost@example.com", role="ghost", hashed_password="x")
    assert scopes_for(ghost) == frozenset()
