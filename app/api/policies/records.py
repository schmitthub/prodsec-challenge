"""Record ownership and composite note access; the reviewed IDOR boundary."""

import uuid
from collections.abc import Sequence
from typing import Annotated, ClassVar, TypedDict

from fastapi import HTTPException, Query
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, func, or_, select

from app.api.deps import CurrentUser, SessionDep
from app.api.policies.base import AuthenticatedPolicy
from app.authz import Binding, Principal
from app.models import Record, RecordBase, RecordNote, RecordNoteBase, UserRole


class RecordPage(TypedDict):
    """Authorized query results; the HTTP response schema owns serialization."""

    data: Sequence[Record]
    count: int


class RecordNotes(TypedDict):
    """Notes selected through an authorized record, before HTTP serialization."""

    record_id: uuid.UUID
    data: Sequence[RecordNote]
    count: int


def record_reader(current_user: CurrentUser) -> None:
    if current_user.role not in (UserRole.member, UserRole.staff):
        raise HTTPException(403, "The user doesn't have enough privileges")


def owned_record(
    record_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Record:
    record = session.exec(
        select(Record).where(Record.id == record_id, Record.user_id == current_user.id)
    ).first()
    if record is None:
        raise HTTPException(404, "Record not found")
    return record


def _page(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int,
    limit: int,
    *filters: ColumnElement[bool],
) -> RecordPage:
    filters = (col(Record.user_id) == current_user.id, *filters)
    count = session.exec(select(func.count()).select_from(Record).where(*filters)).one()
    rows = session.exec(select(Record).where(*filters).offset(skip).limit(limit)).all()
    return RecordPage(data=rows, count=count)


def owned_records(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> RecordPage:
    return _page(session, current_user, skip, limit)


def search_owned_records(
    q: Annotated[str, Query(min_length=1, max_length=255)],
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> RecordPage:
    return _page(
        session,
        current_user,
        skip,
        limit,
        col(Record.summary).icontains(q, autoescape=True),
    )


def owner_or_staff_notes(
    record_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> RecordNotes:
    """Authenticated owner OR staff; only this composite notes operation widens."""
    record = session.exec(
        select(Record).where(
            Record.id == record_id,
            or_(Record.user_id == current_user.id, current_user.role == UserRole.staff),
        )
    ).first()
    if record is None:
        raise HTTPException(404, "Record not found")
    return RecordNotes(record_id=record.id, data=record.notes, count=len(record.notes))


class RecordPolicy(AuthenticatedPolicy):
    principal: ClassVar[Principal] = staticmethod(record_reader)
    record = Binding((RecordBase,), owned_record)
    page = Binding((RecordBase,), owned_records)
    search = Binding((RecordBase,), search_owned_records)


class OwnerOrStaffNotesPolicy(AuthenticatedPolicy):
    principal: ClassVar[Principal] = staticmethod(record_reader)
    notes = Binding((RecordBase, RecordNoteBase), owner_or_staff_notes)
