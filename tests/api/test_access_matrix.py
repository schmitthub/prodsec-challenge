"""Declared policy vs observed behaviour for every API route x principal.

Expected status is derived only from the route's declared policy
(``app.api.policy``), ``ROLE_SCOPES`` and the model's ``__access__``; the
request is then made and the two must agree. A route that grants more or less
than it declares fails here even if PolicyRouter and semgrep were satisfied.

Order of decisions, mirroring the dependency chain: 401 (no principal), then
403 (scope), then 404 (row not visible), then granted. "Granted" means the
request got past access control: any status other than those three, including
422 for routes that need a body we don't supply.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.deps import scopes_for
from app.api.policy import RoutePolicy, api_policies
from app.main import app
from app.models import Record, User
from tests.conftest import MEMBER_EMAIL, OTHER_MEMBER_EMAIL, STAFF_EMAIL
from tests.utils.record import create_random_record
from tests.utils.user import seed_user_token_headers

GRANTED = "granted"
DENIED = {401, 403, 404}


@dataclass(frozen=True)
class Principal:
    name: str
    email: str | None  # None: anonymous


PRINCIPALS = (
    Principal("anonymous", None),
    Principal("owner", MEMBER_EMAIL),
    Principal("other-member", OTHER_MEMBER_EMAIL),
    Principal("staff", STAFF_EMAIL),
)


def expected_status(policy: RoutePolicy, user: User | None, owner: User) -> int | str:
    if policy.public:
        return GRANTED
    if user is None:
        return 401
    granted = {s.value for s in scopes_for(user)}
    if not set(policy.scopes) <= granted:
        return 403
    for row in policy.rows:
        if row.param is None or user.id == owner.id:
            continue  # collections are filtered, never denied; owners always pass
        read_any = row.model.__access__.read_any
        widened = row.marker == "AnyOwner" and read_any in scopes_for(user)
        if not widened:
            return 404
    return GRANTED


def fill_path(policy: RoutePolicy, rows: dict[type, uuid.UUID]) -> str:
    path = policy.path
    for row in policy.rows:
        if row.param is not None:
            path = path.replace("{" + row.param + "}", str(rows[row.model]))
    assert "{" not in path, f"unfilled path parameter in {path}; extend fill_path"
    return path


@pytest.fixture(scope="module")
def owner(db: Session) -> User:
    return db.exec(select(User).where(User.email == MEMBER_EMAIL)).one()


@pytest.fixture(scope="module")
def owner_rows(db: Session, owner: User) -> dict[type, uuid.UUID]:
    """One row per row-loaded model, owned by the owner principal."""
    return {Record: create_random_record(db, user_id=owner.id).id}


@pytest.mark.parametrize("principal", PRINCIPALS, ids=lambda p: p.name)
@pytest.mark.parametrize("policy", api_policies(app), ids=lambda p: p.key)
def test_observed_status_matches_declared_policy(
    client: TestClient,
    db: Session,
    owner: User,
    owner_rows: dict[type, uuid.UUID],
    policy: RoutePolicy,
    principal: Principal,
) -> None:
    for row in policy.rows:
        assert row.model in owner_rows, f"no fixture row for {row.model.__name__}"
    user = (
        None
        if principal.email is None
        else db.exec(select(User).where(User.email == principal.email)).one()
    )
    headers = (
        {}
        if principal.email is None
        else seed_user_token_headers(client=client, email=principal.email)
    )
    expected = expected_status(policy, user, owner)

    response = client.request(
        policy.method,
        fill_path(policy, owner_rows),
        headers=headers,
        params={"q": "a"},  # satisfies routes that require a query; ignored elsewhere
    )
    observed = response.status_code if response.status_code in DENIED else GRANTED
    assert observed == expected, (
        f"{principal.name} on {policy.key}: declared {policy.as_json()} "
        f"=> expected {expected}, got {response.status_code}: {response.text[:200]}"
    )
