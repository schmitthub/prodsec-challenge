from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app import crud
from app.models import User, UserCreate, UserRole
from tests.utils.utils import random_email, random_lower_string


def test_create_user_hashes_password(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )
    assert user.email == email
    assert user.hashed_password != password
    assert user.hashed_password.startswith("$2b$")


def test_authenticate_user(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=password)
    )
    authenticated = crud.authenticate(session=db, email=email, password=password)
    assert authenticated
    assert authenticated.id == user.id


def test_authenticate_wrong_password(db: Session) -> None:
    email = random_email()
    crud.create_user(
        session=db, user_create=UserCreate(email=email, password=random_lower_string())
    )
    assert crud.authenticate(session=db, email=email, password="wrong-password") is None


def test_authenticate_unknown_user(db: Session) -> None:
    assert (
        crud.authenticate(
            session=db, email=random_email(), password=random_lower_string()
        )
        is None
    )


def test_create_staff_user(db: Session) -> None:
    user_in = UserCreate(
        email=random_email(), password=random_lower_string(), role=UserRole.staff
    )
    user = crud.create_user(session=db, user_create=user_in)
    assert user.role == UserRole.staff


def test_default_role_is_member(db: Session) -> None:
    user_in = UserCreate(email=random_email(), password=random_lower_string())
    user = crud.create_user(session=db, user_create=user_in)
    assert user.role == UserRole.member


def test_get_user(db: Session) -> None:
    user_in = UserCreate(email=random_email(), password=random_lower_string())
    user = crud.create_user(session=db, user_create=user_in)
    user_2 = db.get(User, user.id)
    assert user_2
    assert jsonable_encoder(user) == jsonable_encoder(user_2)
    assert crud.get_user_by_email(session=db, email=user.email) == user_2
