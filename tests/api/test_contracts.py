"""Discover the real mounted API; no endpoint manifest or generated expectations."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.policies.records import OwnerOrStaffNotesPolicy, RecordPolicy
from app.api.policies.users import UserPolicy
from app.authz import discover_contracts
from app.core.config import settings
from app.main import app
from app.models import RecordBase, RecordNoteBase, UserRole
from tests.utils.record import create_random_record
from tests.utils.user import random_user_token_headers


@pytest.mark.parametrize(
    "contract",
    [c for c in discover_contracts(app) if not c.public],
    ids=lambda c: f"{c.method} {c.path}",
)
def test_every_protected_operation_requires_identity(
    client: TestClient, contract
) -> None:
    path = contract.path.replace("{record_id}", str(uuid.uuid4()))
    response = client.request(contract.method, path, params={"q": "a"})
    assert response.status_code == 401


def test_live_contracts_reflect_asset_boundaries() -> None:
    contracts = {c.path: c for c in discover_contracts(app)}
    prefix = settings.API_V1_STR
    assert contracts[f"{prefix}/me"].policy is UserPolicy
    assert contracts[f"{prefix}/search"].policy is RecordPolicy
    assert contracts[f"{prefix}/search"].resources == (RecordBase,)
    notes = contracts[f"{prefix}/records/{{record_id}}/notes"]
    assert notes.policy is OwnerOrStaffNotesPolicy
    assert notes.resources == (RecordBase, RecordNoteBase)
    assert notes.overridden


def test_staff_exception_does_not_widen_other_record_operations(
    client: TestClient,
    db: Session,
) -> None:
    staff, headers = random_user_token_headers(
        client=client, db=db, role=UserRole.staff
    )
    own = create_random_record(db, user_id=staff.id, summary="contract-proof")
    foreign = create_random_record(db, summary="contract-proof")
    prefix = settings.API_V1_STR
    denied = client.get(f"{prefix}/records/{foreign.id}", headers=headers)
    missing = client.get(f"{prefix}/records/{uuid.uuid4()}", headers=headers)
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json()
    for path in ("records", "search?q=contract-proof"):
        response = client.get(f"{prefix}/{path}", headers=headers)
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert [r["id"] for r in response.json()["data"]] == [str(own.id)]
