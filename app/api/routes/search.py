from typing import Annotated, Any

from fastapi import Query
from sqlmodel import col

from app.api.deps import OwnedQuery, PolicyRouter
from app.models import Record, RecordsPublic

router = PolicyRouter(tags=["search"])


@router.get("/search", response_model=RecordsPublic)
def search_records(
    q: Annotated[str, Query(min_length=1, max_length=255)],
    records: OwnedQuery[Record],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Case-insensitive substring search over the caller's own record summaries."""
    matches = records.where(col(Record.summary).icontains(q, autoescape=True))
    return RecordsPublic(data=matches.page(skip, limit), count=matches.count())
