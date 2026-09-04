"""Fixture for fastapi-access-control.yaml. Not application code.

A comment naming a rule id with the "required finding" marker makes the next
statement an expected match; the "non-finding" marker makes it an expected
non-match. The semgrep prek hook runs this (via semgrep_gate.py) before every
local scan:

    prek run semgrep --all-files

The rules scope themselves to app/api/routes/ via `paths`, which semgrep
ignores in test mode, so this file is never a finding in a normal scan.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.deps import (
    PUBLIC,
    AnyOwner,
    CurrentUser,
    Owned,
    OwnedQuery,
    PolicyRouter,
    SessionDep,
    get_current_user,
    require,
)
from app.models import Record, RecordPublic, RecordsPublic, Scope, User

# ruleid: fastapi-router-not-policy-router
legacy = APIRouter(tags=["legacy"])
# ok: fastapi-router-not-policy-router
router = PolicyRouter(tags=["records"])


# ok: fastapi-route-session-param
@router.post("/login", dependencies=[PUBLIC])
# ruleid: fastapi-escape-hatch
def login(session: SessionDep) -> Any:
    return session


@router.get("/records/{record_id}")
# ruleid: fastapi-route-session-param
def read_record_with_session(session: SessionDep, record_id: str) -> Any:
    return session.get(str, record_id)


@router.get("/records/{record_id}")
# ruleid: fastapi-route-session-param
def read_record_bare_session(session: Session, record_id: str) -> Any:
    return session.get(str, record_id)


@router.get("/records/{record_id}")
# ok: fastapi-route-session-param
# ok: fastapi-route-model-param-unwrapped
# ok: fastapi-route-path-model-mismatch
def read_record(record: Owned[Record]) -> Any:
    return record


@router.get("/records/{record_id}/notes")
# ok: fastapi-route-model-param-unwrapped
def read_notes(record: AnyOwner[Record]) -> Any:
    return record.notes


@router.get("/records")
# ok: fastapi-route-model-param-unwrapped
def list_records(records: OwnedQuery[Record], skip: int = 0) -> Any:
    return RecordsPublic(data=records.page(skip, 100), count=records.count())


@router.get("/records/{record_id}")
# ruleid: fastapi-route-model-param-unwrapped
def read_record_unwrapped(record: Record) -> Any:
    return record


@router.get("/records/{record_id}")
# ruleid: fastapi-route-model-param-unwrapped
def read_record_annotated(record: Annotated[Record, Depends(get_current_user)]) -> Any:
    return record


@router.get("/me")
# ok: fastapi-route-model-param-unwrapped
def read_me(current_user: CurrentUser) -> Any:
    return current_user


@router.get("/search")
# ok: fastapi-route-model-param-unwrapped
def search(q: Annotated[str, Query(min_length=1)], records: OwnedQuery[Record]) -> Any:
    return records.where(q)


# ok: fastapi-route-foreign-dependency
@router.post("/webhooks/vendor-preview", dependencies=[require(Scope.webhooks_preview)])
def preview_ok() -> Any:
    return {}


# ruleid: fastapi-route-foreign-dependency
@router.post("/webhooks/vendor-preview", dependencies=[Depends(get_current_user)])
def preview_depends() -> Any:
    return {}


def staff_only() -> Any:
    return Depends(get_current_user)


# ruleid: fastapi-route-foreign-dependency
@router.post("/webhooks/vendor-preview", dependencies=[staff_only()])
def preview_wrapper() -> Any:
    return {}


@router.post(
    "/webhooks/vendor-preview",
    # ruleid: fastapi-route-foreign-dependency
    dependencies=[require(Scope.staff), Depends(get_current_user)],
)
def preview_mixed() -> Any:
    return {}


# ok: fastapi-require-string-scope
ok_scope = require(Scope.staff)
# ruleid: fastapi-require-string-scope
bad_scope = require("role:staff")


def inline_checks(current_user: User, record: Record) -> None:
    # ruleid: fastapi-inline-role-check
    if current_user.role != "staff" and record.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Record not found")
    # ruleid: fastapi-inline-role-check
    if current_user.role == "staff":
        return None
    # ruleid: fastapi-inline-role-check
    if current_user.role in {"staff"}:
        return None
    # ok: fastapi-inline-role-check
    if record.user_id != current_user.id:
        return None


def raises() -> None:
    # ruleid: fastapi-route-raises-403
    raise HTTPException(status_code=403, detail="nope")


def raises_const() -> None:
    # ruleid: fastapi-route-raises-403
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="nope")


def raises_positional() -> None:
    # ruleid: fastapi-route-raises-403
    raise HTTPException(403, "nope")


def raises_404() -> None:
    # ok: fastapi-route-raises-403
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
    )


@router.get("/records/{record_id}", dependencies=[PUBLIC])
# ruleid: fastapi-escape-hatch
def raw_get(session: SessionDep, record_id: str) -> Any:
    record = session.get(Record, record_id)
    # ruleid: fastapi-route-raw-row-to-response
    return record


@router.get("/records", dependencies=[PUBLIC])
# ruleid: fastapi-escape-hatch
def raw_select(session: SessionDep) -> Any:
    rows = session.exec(select(Record)).all()
    # ruleid: fastapi-route-raw-row-to-response
    return RecordsPublic(data=rows, count=len(rows))


@router.get("/records/{record_id}")
def loader_row(record: Owned[Record]) -> Any:
    # ok: fastapi-route-raw-row-to-response
    return RecordPublic.model_validate(record)


@router.get("/records/{record_id}")
# ruleid: fastapi-route-path-model-mismatch
def path_mismatch(user: Owned[User]) -> Any:
    return user


@router.get("/users/{user_id}")
# ok: fastapi-route-path-model-mismatch
def path_other(user: Owned[User]) -> Any:
    return user
