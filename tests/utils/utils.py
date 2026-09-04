import random
import string

from fastapi.testclient import TestClient

from app.core.config import settings


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def login_token_headers(
    client: TestClient, *, email: str, password: str
) -> dict[str, str]:
    # OAuth2 password grant: form-encoded, ``username`` carries the email.
    r = client.post(
        f"{settings.API_V1_STR}/login",
        data={"grant_type": "password", "username": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
