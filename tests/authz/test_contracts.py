from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.authz import (
    PUBLIC,
    Binding,
    FromPolicy,
    Policy,
    PolicyError,
    PolicyRouter,
    discover_contracts,
    use_policy,
)


class Document:
    pass


class Comment:
    pass


def identity() -> str:
    raise HTTPException(401, "Not authenticated")


def load_document(key: int) -> dict[str, int]:
    return {"id": key}


def load_comments(key: int) -> list[int]:
    return [key]


class Documents(Policy):
    principal = staticmethod(identity)
    document = Binding((Document,), load_document)


class Discussion(Policy):
    principal = staticmethod(identity)
    document = Documents.document
    comments = Binding((Document, Comment), load_comments)


class PublicDocuments(Policy):
    principal = PUBLIC
    document = Documents.document


def test_router_requires_policy() -> None:
    with pytest.raises(TypeError, match="protected_policy"):
        PolicyRouter()


def test_policy_requires_explicit_principal() -> None:
    class MissingPrincipal(Policy):
        document = Documents.document

    with pytest.raises(PolicyError, match="principal"):
        PolicyRouter(protected_policy=MissingPrincipal)


def test_policy_requires_resource_bindings() -> None:
    class Empty(Policy):
        principal = staticmethod(identity)

    with pytest.raises(PolicyError, match="binding"):
        PolicyRouter(protected_policy=Empty)


def test_authentication_precedes_provider_and_validation() -> None:
    router = PolicyRouter(protected_policy=Documents)

    @router.get("/{key}")
    def read(data: Annotated[dict[str, int], FromPolicy(Documents.document)]):
        return data

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/not-an-integer").status_code == 401
    app.dependency_overrides[identity] = lambda: "alice"
    assert client.get("/42").json() == {"id": 42}


@pytest.mark.parametrize("public_result", [False, True])
def test_asset_family_allows_sibling_results_with_public_projection(
    public_result: bool,
) -> None:
    class Asset(BaseModel):
        title: str

    class Stored(Asset):
        id: int
        internal: str

    class PublicView(Asset):
        id: int

    def load(key: int) -> Asset:
        if public_result:
            return PublicView(id=key, title="Example")
        return Stored(id=key, title="Example", internal="provider-only data")

    class AssetPolicy(Policy):
        principal = staticmethod(identity)
        item = Binding((Asset,), load)

    router = PolicyRouter(protected_policy=AssetPolicy)

    @router.get("/{key}", response_model=PublicView)
    def read(item: Annotated[Asset, FromPolicy(AssetPolicy.item)]) -> Asset:
        return item

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/42").status_code == 401
    app.dependency_overrides[identity] = lambda: "alice"
    response = client.get("/42")
    assert response.status_code == 200
    assert response.json() == {"id": 42, "title": "Example"}
    assert discover_contracts(app)[0].resources == (Asset,)


def test_unbound_endpoint_fails_registration() -> None:
    router = PolicyRouter(protected_policy=Documents)
    with pytest.raises(PolicyError, match="FromPolicy"):

        @router.get("/unbound")
        def read():
            return {"id": 42}


def test_foreign_binding_fails_registration() -> None:
    router = PolicyRouter(protected_policy=Documents)
    with pytest.raises(PolicyError, match="does not belong"):

        @router.get("/{key}")
        def read(data: Annotated[list[int], FromPolicy(Discussion.comments)]):
            return data


def test_raw_dependency_cannot_bypass_binding() -> None:
    router = PolicyRouter(protected_policy=Documents)
    with pytest.raises(PolicyError, match="FromPolicy"):

        @router.get("/{key}")
        def read(data: Annotated[dict[str, int], Depends(load_document)]):
            return data


def test_composite_policy_executes_each_binding() -> None:
    router = PolicyRouter(protected_policy=Documents)

    @router.get("/{key}", dependencies=[use_policy(Discussion)])
    async def read(
        document: Annotated[dict[str, int], FromPolicy(Discussion.document)],
        comments: Annotated[list[int], FromPolicy(Discussion.comments)],
    ):
        return {"document": document, "comments": comments}

    app = FastAPI()
    app.include_router(router, prefix="/v1")
    app.dependency_overrides[identity] = lambda: "alice"
    assert TestClient(app).get("/v1/7").json() == {
        "document": {"id": 7},
        "comments": [7],
    }
    (contract,) = discover_contracts(app)
    assert contract.policy is Discussion
    assert contract.overridden
    assert contract.resources == (Document, Comment)


def test_public_is_explicit_and_discoverable() -> None:
    router = PolicyRouter(protected_policy=PublicDocuments)

    @router.get("/{key}")
    def read(data: Annotated[dict[str, int], FromPolicy(PublicDocuments.document)]):
        return data

    app = FastAPI()
    app.include_router(router)
    assert TestClient(app).get("/3").status_code == 200
    assert discover_contracts(app)[0].public


def test_hidden_and_nested_uncontracted_routes_are_rejected() -> None:
    child = APIRouter()

    @child.get("/unprotected", include_in_schema=False)
    def unprotected():
        return {}

    parent = APIRouter()
    parent.include_router(child, prefix="/nested")
    app = FastAPI()
    app.include_router(parent, prefix="/v1")
    with pytest.raises(PolicyError, match="/v1/nested/unprotected"):
        discover_contracts(app)


def test_read_policy_cannot_silently_authorize_writes() -> None:
    router = PolicyRouter(protected_policy=Documents)
    with pytest.raises(PolicyError, match="method"):

        @router.post("/{key}")
        def write(data: Annotated[dict[str, int], FromPolicy(Documents.document)]):
            return data


def test_endpoint_function_is_not_rewritten() -> None:
    def read(data: Annotated[dict[str, int], FromPolicy(Documents.document)]):
        return data

    for policy in (Documents, PublicDocuments):
        router = PolicyRouter(protected_policy=policy)
        router.add_api_route("/{key}", read, methods=["GET"])
    assert "__signature__" not in read.__dict__


def test_unused_bindings_do_not_execute() -> None:
    def unrelated() -> str:
        raise AssertionError("declaring a resource must not load it")

    class Extended(Documents):
        unused = Binding((Comment,), unrelated)

    router = PolicyRouter(protected_policy=Extended)

    @router.get("/{key}")
    def read(data: Annotated[dict[str, int], FromPolicy(Extended.document)]):
        return data

    app = FastAPI()
    app.dependency_overrides[identity] = lambda: "alice"
    app.include_router(router)
    assert TestClient(app).get("/9").json() == {"id": 9}


def test_discovery_detects_disconnected_authorization() -> None:
    router = PolicyRouter(protected_policy=Documents)

    @router.get("/{key}")
    def read(data: Annotated[dict[str, int], FromPolicy(Documents.document)]):
        return data

    app = FastAPI()
    app.router.routes.extend(router.routes)
    discover_contracts(app)
    router.routes[0].dependant.dependencies.clear()
    with pytest.raises(PolicyError, match="not wired"):
        discover_contracts(app)


def test_duplicate_overrides_and_raw_decorator_dependencies_are_rejected() -> None:
    router = PolicyRouter(protected_policy=Documents)
    for dependencies in (
        [use_policy(Discussion), use_policy(PublicDocuments)],
        [Depends(identity)],
    ):
        with pytest.raises(PolicyError, match="one use_policy"):

            @router.get("/{key}", dependencies=dependencies)
            def read(data: Annotated[dict[str, int], FromPolicy(Documents.document)]):
                return data


def test_uncontracted_subapplication_is_not_silently_skipped() -> None:
    app = FastAPI()
    app.mount("/other", FastAPI())
    with pytest.raises(PolicyError, match="/other"):
        discover_contracts(app)
