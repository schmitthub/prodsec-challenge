from typing import Annotated

from app.api.policies.records import (
    OwnerOrStaffNotesPolicy,
    RecordNotes,
    RecordPage,
    RecordPolicy,
)
from app.authz import FromPolicy, PolicyRouter, use_policy
from app.models import Record, RecordNotesPublic, RecordPublic, RecordsPublic

router = PolicyRouter(tags=["records"], protected_policy=RecordPolicy)


@router.get("/records", response_model=RecordsPublic)
def list_my_records(
    records: Annotated[RecordPage, FromPolicy(RecordPolicy.page)],
) -> RecordPage:
    return records


@router.get("/records/{record_id}", response_model=RecordPublic)
def read_record(record: Annotated[Record, FromPolicy(RecordPolicy.record)]) -> Record:
    return record


@router.get(
    "/records/{record_id}/notes",
    response_model=RecordNotesPublic,
    dependencies=[
        # Product exception: record owners and staff may read this record's notes.
        # nosemgrep: authz-policy-override
        use_policy(OwnerOrStaffNotesPolicy)
    ],
)
def read_record_notes(
    notes: Annotated[RecordNotes, FromPolicy(OwnerOrStaffNotesPolicy.notes)],
) -> RecordNotes:
    return notes
