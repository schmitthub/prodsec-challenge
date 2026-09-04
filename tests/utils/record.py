import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    Record,
    RecordCreate,
    RecordNote,
    RecordNoteCreate,
    RecordStatus,
    RecordType,
)
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def create_random_record(
    db: Session, *, user_id: uuid.UUID | None = None, summary: str | None = None
) -> Record:
    if user_id is None:
        user_id = create_random_user(db).id
    record_in = RecordCreate(
        type=RecordType.lab_result,
        status=RecordStatus.released,
        summary=summary if summary is not None else random_lower_string(),
    )
    return crud.create_record(session=db, record_in=record_in, owner_id=user_id)


def create_random_record_note(
    db: Session, *, record_id: uuid.UUID | None = None
) -> RecordNote:
    if record_id is None:
        record_id = create_random_record(db).id
    note_in = RecordNoteCreate(note=random_lower_string())
    return crud.create_record_note(
        session=db, record_note_in=note_in, record_id=record_id
    )
