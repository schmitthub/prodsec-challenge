from __future__ import annotations

import email_validator
from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import (
    Record,
    RecordCreate,
    RecordNote,
    RecordNoteCreate,
    RecordStatus,
    RecordType,
    User,
    UserCreate,
    UserRole,
)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


# Local-only fixture accounts. Password comes from settings.SEED_PASSWORD.
SEED_USERS: list[dict] = [
    {"email": "alice@example.test", "role": UserRole.member},
    {"email": "bob@example.test", "role": UserRole.member},
    {"email": "clinician@example.test", "role": UserRole.staff},
]

# Records keyed by owner email; notes keyed by record summary.
SEED_RECORDS: list[dict] = [
    {
        "owner_email": "alice@example.test",
        "type": RecordType.lab_result,
        "status": RecordStatus.released,
        "summary": "A1C within expected range",
        "notes": ["Reviewed with patient", "Repeat in 6 months"],
    },
    {
        "owner_email": "bob@example.test",
        "type": RecordType.lab_result,
        "status": RecordStatus.released,
        "summary": "LDL elevated; follow-up recommended",
        "notes": ["Statin discussed", "Recheck lipids in 12 weeks"],
    },
]


def _get_or_create_user(session: Session, *, email: str, role: UserRole) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user:
        return user
    return crud.create_user(
        session=session,
        user_create=UserCreate(email=email, password=settings.SEED_PASSWORD, role=role),
    )


def _get_or_create_record(
    session: Session,
    *,
    owner: User,
    type: RecordType,
    status: RecordStatus,
    summary: str,
) -> Record:
    record = session.exec(
        select(Record).where(Record.user_id == owner.id, Record.summary == summary)
    ).first()
    if record:
        return record
    return crud.create_record(
        session=session,
        record_in=RecordCreate(type=type, status=status, summary=summary),
        owner_id=owner.id,
    )


def _get_or_create_note(session: Session, *, record: Record, note: str) -> RecordNote:
    existing = session.exec(
        select(RecordNote).where(
            RecordNote.record_id == record.id, RecordNote.note == note
        )
    ).first()
    if existing:
        return existing
    return crud.create_record_note(
        session=session,
        record_note_in=RecordNoteCreate(note=note),
        record_id=record.id,
    )


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    if settings.ENVIRONMENT != "local":
        return

    # Fixture accounts live on the reserved .test TLD, which email-validator
    # rejects outside test mode.
    email_validator.TEST_ENVIRONMENT = True

    # Idempotent: every step is a lookup by natural key before insert, so a
    # partially or fully seeded database is left as-is.
    users = {
        u["email"]: _get_or_create_user(session, email=u["email"], role=u["role"])
        for u in SEED_USERS
    }

    for r in SEED_RECORDS:
        record = _get_or_create_record(
            session,
            owner=users[r["owner_email"]],
            type=r["type"],
            status=r["status"],
            summary=r["summary"],
        )
        for note in r["notes"]:
            _get_or_create_note(session, record=record, note=note)
