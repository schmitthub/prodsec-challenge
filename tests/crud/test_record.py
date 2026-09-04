from sqlmodel import Session

from app import crud
from app.models import Record, RecordCreate, RecordNoteCreate, RecordStatus, RecordType
from tests.utils.record import create_random_record, create_random_record_note
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def test_create_record(db: Session) -> None:
    user = create_random_user(db)
    summary = random_lower_string()
    record_in = RecordCreate(
        type=RecordType.lab_result, status=RecordStatus.released, summary=summary
    )
    record = crud.create_record(session=db, record_in=record_in, owner_id=user.id)
    assert record.id
    assert record.user_id == user.id
    assert record.summary == summary
    assert db.get(Record, record.id) == record


def test_record_belongs_to_user_relationship(db: Session) -> None:
    user = create_random_user(db)
    record = create_random_record(db, user_id=user.id)
    db.refresh(user)
    assert record in user.records
    assert record.user == user


def test_create_record_note(db: Session) -> None:
    record = create_random_record(db)
    text = random_lower_string()
    note = crud.create_record_note(
        session=db, record_note_in=RecordNoteCreate(note=text), record_id=record.id
    )
    assert note.record_id == record.id
    assert note.note == text
    db.refresh(record)
    assert note in record.notes


def test_random_record_note_creates_owner_chain(db: Session) -> None:
    note = create_random_record_note(db)
    record = db.get(Record, note.record_id)
    assert record is not None
    assert record.user is not None
