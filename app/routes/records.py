from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app import db
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/me")
def read_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("/records")
def list_my_records(current_user: Annotated[User, Depends(get_current_user)]):
    return db.list_records_for_user(current_user.id)


@router.get("/records/{record_id}")
def read_record(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )

    return record


@router.get("/records/{record_id}/notes")
def read_record_notes(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    record = db.get_record(record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )

    if current_user.role != "staff" and record["owner_user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )

    return {
        "record_id": record_id,
        "notes": ["Reviewed by clinical operations", "Visible after release"],
    }
