from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Record, RecordsPublic

router = APIRouter(tags=["search"])


@router.get("/search", response_model=RecordsPublic)
def search_records(
    q: Annotated[str, Query(min_length=1, max_length=255)],
    current_user: CurrentUser,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Case-insensitive substring search over the caller's own record summaries."""
    filters = (
        Record.user_id == current_user.id,
        col(Record.summary).icontains(q, autoescape=True),
    )
    count_statement = select(func.count()).select_from(Record).where(*filters)
    count = session.exec(count_statement).one()
    statement = select(Record).where(*filters).offset(skip).limit(limit)
    records = session.exec(statement).all()

    return RecordsPublic(data=records, count=count)
