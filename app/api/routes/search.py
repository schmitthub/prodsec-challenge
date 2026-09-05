from typing import Annotated

from app.api.policies.records import RecordPage, RecordPolicy
from app.authz import FromPolicy, PolicyRouter
from app.models import RecordsPublic

router = PolicyRouter(tags=["search"], protected_policy=RecordPolicy)


@router.get("/search", response_model=RecordsPublic)
def search_records(
    records: Annotated[RecordPage, FromPolicy(RecordPolicy.search)],
) -> RecordPage:
    return records
