import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import UserRole
from tests.utils.record import create_random_record, create_random_record_note
from tests.utils.user import random_user_token_headers


def test_health_check(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_my_records(client: TestClient, db: Session) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    own = {str(create_random_record(db, user_id=user.id).id) for _ in range(2)}
    create_random_record(db)  # someone else's

    r = client.get(f"{settings.API_V1_STR}/records", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert {rec["id"] for rec in body["data"]} == own
    assert all(rec["user_id"] == str(user.id) for rec in body["data"])


def test_list_records_pagination(client: TestClient, db: Session) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    for _ in range(3):
        create_random_record(db, user_id=user.id)

    r = client.get(
        f"{settings.API_V1_STR}/records",
        params={"skip": 1, "limit": 1},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 3
    assert len(body["data"]) == 1


def test_list_records_unauthenticated(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/records")
    assert r.status_code == 401


def test_read_own_record(client: TestClient, db: Session) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    record = create_random_record(db, user_id=user.id)

    r = client.get(f"{settings.API_V1_STR}/records/{record.id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(record.id)
    assert body["user_id"] == str(user.id)
    assert body["summary"] == record.summary


def test_read_other_users_record_is_not_found(client: TestClient, db: Session) -> None:
    _, headers = random_user_token_headers(client=client, db=db)
    foreign = create_random_record(db)

    r = client.get(f"{settings.API_V1_STR}/records/{foreign.id}", headers=headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "Record not found"


def test_read_record_missing(client: TestClient, db: Session) -> None:
    _, headers = random_user_token_headers(client=client, db=db)
    r = client.get(f"{settings.API_V1_STR}/records/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404


def test_read_record_invalid_id(client: TestClient, db: Session) -> None:
    _, headers = random_user_token_headers(client=client, db=db)
    r = client.get(f"{settings.API_V1_STR}/records/not-a-uuid", headers=headers)
    assert r.status_code == 422


def test_read_own_record_notes(client: TestClient, db: Session) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    record = create_random_record(db, user_id=user.id)
    notes = {
        str(create_random_record_note(db, record_id=record.id).id) for _ in range(2)
    }

    r = client.get(f"{settings.API_V1_STR}/records/{record.id}/notes", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["record_id"] == str(record.id)
    assert body["count"] == 2
    assert {n["id"] for n in body["data"]} == notes
    assert all(n["record_id"] == str(record.id) for n in body["data"])


def test_read_other_users_record_notes_is_not_found(
    client: TestClient, db: Session
) -> None:
    _, headers = random_user_token_headers(client=client, db=db)
    foreign = create_random_record(db)
    create_random_record_note(db, record_id=foreign.id)

    r = client.get(f"{settings.API_V1_STR}/records/{foreign.id}/notes", headers=headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "Record not found"


def test_staff_can_read_any_record_notes(client: TestClient, db: Session) -> None:
    _, staff_headers = random_user_token_headers(
        client=client, db=db, role=UserRole.staff
    )
    record = create_random_record(db)
    note = create_random_record_note(db, record_id=record.id)

    r = client.get(
        f"{settings.API_V1_STR}/records/{record.id}/notes", headers=staff_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["record_id"] == str(record.id)
    assert [n["id"] for n in body["data"]] == [str(note.id)]


def test_staff_record_notes_missing(client: TestClient, db: Session) -> None:
    _, staff_headers = random_user_token_headers(
        client=client, db=db, role=UserRole.staff
    )
    r = client.get(
        f"{settings.API_V1_STR}/records/{uuid.uuid4()}/notes", headers=staff_headers
    )
    assert r.status_code == 404


def test_read_record_notes_unauthenticated(client: TestClient, db: Session) -> None:
    record = create_random_record(db)
    r = client.get(f"{settings.API_V1_STR}/records/{record.id}/notes")
    assert r.status_code == 401
