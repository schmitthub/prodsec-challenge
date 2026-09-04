import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Record,
    RecordNotesPublic,
    RecordPublic,
    RecordsPublic,
    UserPublic,
)

router = APIRouter(tags=["records"])


@router.get("/me", response_model=UserPublic)
def read_me(current_user: CurrentUser) -> Any:
    return current_user


@router.get("/records", response_model=RecordsPublic)
def list_my_records(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    count_statement = (
        select(func.count())
        .select_from(Record)
        .where(Record.user_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Record)
        .where(Record.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    records = session.exec(statement).all()

    return RecordsPublic(data=records, count=count)


@router.get("/records/{record_id}", response_model=RecordPublic)
def read_record(
    session: SessionDep, current_user: CurrentUser, record_id: uuid.UUID
) -> Any:
    record = session.get(Record, record_id)
    if not record or record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )

    return record


@router.get("/records/{record_id}/notes", response_model=RecordNotesPublic)
def read_record_notes(
    session: SessionDep, current_user: CurrentUser, record_id: uuid.UUID
) -> Any:
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    if current_user.role != "staff" and record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )

    return RecordNotesPublic(
        record_id=record.id,
        data=record.notes,
        count=len(record.notes),
    )
