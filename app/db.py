from __future__ import annotations

import sqlite3
from typing import Any

USERS = {
    "user_alice": {
        "id": "user_alice",
        "email": "alice@example.test",
        "password": "alice-password",
        "role": "member",
    },
    "user_bob": {
        "id": "user_bob",
        "email": "bob@example.test",
        "password": "bob-password",
        "role": "member",
    },
    "user_clinician": {
        "id": "user_clinician",
        "email": "clinician@example.test",
        "password": "clinician-password",
        "role": "staff",
    },
}

RECORDS = {
    "rec_alice_001": {
        "id": "rec_alice_001",
        "owner_user_id": "user_alice",
        "record_type": "lab_result",
        "status": "released",
        "summary": "A1C within expected range",
    },
    "rec_bob_001": {
        "id": "rec_bob_001",
        "owner_user_id": "user_bob",
        "record_type": "lab_result",
        "status": "released",
        "summary": "LDL elevated; follow-up recommended",
    },
}


def get_user_by_email(email: str) -> dict[str, Any] | None:
    for user in USERS.values():
        if user["email"] == email:
            return user
    return None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    return USERS.get(user_id)


def get_record(record_id: str) -> dict[str, Any] | None:
    return RECORDS.get(record_id)


def list_records_for_user(user_id: str) -> list[dict[str, Any]]:
    return [record for record in RECORDS.values() if record["owner_user_id"] == user_id]


def search_records(term: str) -> list[dict[str, Any]]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE records (id TEXT, owner_user_id TEXT, record_type TEXT, status TEXT, summary TEXT)"
    )
    connection.executemany(
        "INSERT INTO records VALUES (:id, :owner_user_id, :record_type, :status, :summary)",
        RECORDS.values(),
    )

    query = (
        f"SELECT * FROM records WHERE status = 'released' AND summary LIKE '%{term}%'"
    )
    rows = connection.execute(query).fetchall()
    connection.close()
    return [dict(row) for row in rows]
