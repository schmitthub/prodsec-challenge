from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User, UserCreate, UserRole
from tests.utils.utils import login_token_headers, random_email, random_lower_string


def create_random_user(db: Session, *, role: UserRole = UserRole.member) -> User:
    user, _password = create_random_user_with_password(db, role=role)
    return user


def create_random_user_with_password(
    db: Session, *, role: UserRole = UserRole.member
) -> tuple[User, str]:
    password = random_lower_string()
    user_in = UserCreate(email=random_email(), password=password, role=role)
    return crud.create_user(session=db, user_create=user_in), password


def random_user_token_headers(
    *, client: TestClient, db: Session, role: UserRole = UserRole.member
) -> tuple[User, dict[str, str]]:
    """Create a fresh user and return it with a bearer header for it."""
    user, password = create_random_user_with_password(db, role=role)
    return user, login_token_headers(client, email=user.email, password=password)


def seed_user_token_headers(*, client: TestClient, email: str) -> dict[str, str]:
    """Bearer header for one of the local fixture accounts seeded by init_db."""
    return login_token_headers(client, email=email, password=settings.SEED_PASSWORD)
