from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from tests.conftest import MEMBER_EMAIL
from tests.utils.user import create_random_user_with_password
from tests.utils.utils import random_email, random_lower_string

LOGIN = f"{settings.API_V1_STR}/login"


def _form(email: str, password: str, **extra) -> dict[str, str]:
    return {"grant_type": "password", "username": email, "password": password, **extra}


def test_login_seed_user(client: TestClient) -> None:
    r = client.post(LOGIN, data=_form(MEMBER_EMAIL, settings.SEED_PASSWORD))
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert r.headers["cache-control"] == "no-store"
    assert r.headers["pragma"] == "no-cache"


def test_login_random_user(client: TestClient, db: Session) -> None:
    user, password = create_random_user_with_password(db)
    r = client.post(LOGIN, data=_form(user.email, password))
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_grant_type_is_optional(client: TestClient) -> None:
    r = client.post(
        LOGIN, data={"username": MEMBER_EMAIL, "password": settings.SEED_PASSWORD}
    )
    assert r.status_code == 200


def test_login_rejects_other_grant_types(client: TestClient) -> None:
    r = client.post(
        LOGIN,
        data=_form(
            MEMBER_EMAIL, settings.SEED_PASSWORD, grant_type="client_credentials"
        ),
    )
    assert r.status_code == 422


def test_login_rejects_json_body(client: TestClient) -> None:
    r = client.post(
        LOGIN, json={"username": MEMBER_EMAIL, "password": settings.SEED_PASSWORD}
    )
    assert r.status_code == 422


def test_login_incorrect_password(client: TestClient) -> None:
    r = client.post(LOGIN, data=_form(MEMBER_EMAIL, "incorrect"))
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "invalid_grant"
    assert body["error_description"] == "Invalid email or password"
    assert r.headers["cache-control"] == "no-store"


def test_login_unknown_user_same_error_as_bad_password(client: TestClient) -> None:
    r = client.post(LOGIN, data=_form(random_email(), random_lower_string()))
    assert r.status_code == 400
    body = r.json()
    assert body["error"] == "invalid_grant"
    assert body["error_description"] == "Invalid email or password"


def test_use_access_token(
    client: TestClient, member_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{settings.API_V1_STR}/me", headers=member_token_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == MEMBER_EMAIL
    assert "hashed_password" not in body


def test_me_without_token(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/me")
    assert r.status_code == 401


def test_me_with_garbage_token(client: TestClient) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert r.status_code == 403


def test_openapi_declares_password_flow_at_login(client: TestClient) -> None:
    schemes = client.get("/api/v1/openapi.json").json()["components"]["securitySchemes"]
    flows = schemes["Bearer"]["flows"]
    assert flows["password"]["tokenUrl"] == LOGIN
