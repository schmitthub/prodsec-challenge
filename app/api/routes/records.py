from typing import Any

from app.api.deps import AnyOwner, CurrentUser, Owned, OwnedQuery, PolicyRouter
from app.models import (
    Record,
    RecordNotesPublic,
    RecordPublic,
    RecordsPublic,
    UserPublic,
)

router = PolicyRouter(tags=["records"])


@router.get("/me", response_model=UserPublic)
def read_me(current_user: CurrentUser) -> Any:
    return current_user


@router.get("/records", response_model=RecordsPublic)
def list_my_records(
    records: OwnedQuery[Record], skip: int = 0, limit: int = 100
) -> Any:
    return RecordsPublic(data=records.page(skip, limit), count=records.count())


@router.get("/records/{record_id}", response_model=RecordPublic)
def read_record(record: Owned[Record]) -> Any:
    return record


@router.get("/records/{record_id}/notes", response_model=RecordNotesPublic)
def read_record_notes(record: AnyOwner[Record]) -> Any:
    return RecordNotesPublic(
        record_id=record.id,
        data=record.notes,
        count=len(record.notes),
    )
