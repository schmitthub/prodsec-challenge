from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.db import engine, init_db
from app.main import app
from app.models import Record, RecordNote, User
from tests.utils.user import seed_user_token_headers

MEMBER_EMAIL = "alice@example.com"
OTHER_MEMBER_EMAIL = "bob@example.com"
STAFF_EMAIL = "clinician@example.com"


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        init_db(session)
        yield session
        session.execute(delete(RecordNote))
        session.execute(delete(Record))
        session.execute(delete(User))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def member_token_headers(client: TestClient) -> dict[str, str]:
    return seed_user_token_headers(client=client, email=MEMBER_EMAIL)


@pytest.fixture(scope="module")
def other_member_token_headers(client: TestClient) -> dict[str, str]:
    return seed_user_token_headers(client=client, email=OTHER_MEMBER_EMAIL)


@pytest.fixture(scope="module")
def staff_token_headers(client: TestClient) -> dict[str, str]:
    return seed_user_token_headers(client=client, email=STAFF_EMAIL)
