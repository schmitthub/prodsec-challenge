import uuid

from sqlmodel import Session, select

from app.core.security import (
    get_password_hash,
    verify_password,
)
from app.models import (
    Record,
    RecordCreate,
    RecordNote,
    RecordNoteCreate,
    User,
    UserCreate,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_record(
    *, session: Session, record_in: RecordCreate, owner_id: uuid.UUID
) -> Record:
    db_item = Record.model_validate(record_in, update={"user_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def create_record_note(
    *, session: Session, record_note_in: RecordNoteCreate, record_id: uuid.UUID
) -> RecordNote:
    db_item = RecordNote.model_validate(record_note_in, update={"record_id": record_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
