from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session

from app.core.config import settings
from tests.utils.record import create_random_record
from tests.utils.user import random_user_token_headers
from tests.utils.utils import random_lower_string


def _search(
    client: TestClient, headers: dict[str, str], q: str, **params: int
) -> Response:
    return client.get(
        f"{settings.API_V1_STR}/search", params={"q": q, **params}, headers=headers
    )


def test_search_matches_own_summary_case_insensitively(
    client: TestClient, db: Session
) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    needle = random_lower_string()
    hit = create_random_record(db, user_id=user.id, summary=f"LDL {needle} elevated")
    create_random_record(db, user_id=user.id, summary="unrelated")

    r = _search(client, headers, needle.upper())
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert [rec["id"] for rec in body["data"]] == [str(hit.id)]


def test_search_is_scoped_to_caller(client: TestClient, db: Session) -> None:
    needle = random_lower_string()
    create_random_record(db, summary=needle)  # another user's record
    _, headers = random_user_token_headers(client=client, db=db)

    r = _search(client, headers, needle)
    assert r.status_code == 200
    assert r.json() == {"data": [], "count": 0}


def test_search_like_metacharacters_are_literal(
    client: TestClient, db: Session
) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    create_random_record(db, user_id=user.id, summary=random_lower_string())

    r = _search(client, headers, "%")
    assert r.status_code == 200
    assert r.json()["count"] == 0

    r = _search(client, headers, "_")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_search_pagination(client: TestClient, db: Session) -> None:
    user, headers = random_user_token_headers(client=client, db=db)
    needle = random_lower_string()
    for i in range(3):
        create_random_record(db, user_id=user.id, summary=f"{needle} {i}")

    r = _search(client, headers, needle, skip=2, limit=5)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 3
    assert len(body["data"]) == 1


def test_search_requires_query(client: TestClient, db: Session) -> None:
    _, headers = random_user_token_headers(client=client, db=db)
    r = client.get(f"{settings.API_V1_STR}/search", headers=headers)
    assert r.status_code == 422
    r = _search(client, headers, "")
    assert r.status_code == 422
    r = _search(client, headers, "x" * 256)
    assert r.status_code == 422


def test_search_unauthenticated(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/search", params={"q": "a"})
    assert r.status_code == 401
