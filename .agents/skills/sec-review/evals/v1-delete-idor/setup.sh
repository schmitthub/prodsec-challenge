#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# cases.md V1: a SQLModel delete route with authentication but no owner check.
cat >> app/api/routes/records.py <<'PY'


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    session: SessionDep,
    current_user: CurrentUser,
    record_id: uuid.UUID,
) -> None:
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    session.delete(record)
    session.commit()
PY
uv sync --quiet
