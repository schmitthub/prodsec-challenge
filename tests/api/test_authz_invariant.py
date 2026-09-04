"""Cross-user identifier invariant: a member never receives another user's identifiers.

Walks every authenticated GET route in the app's OpenAPI schema and calls it as
each seeded member-role user, substituting other users' identifiers (their user
id and the ids of records they own) into path parameters and an empty value into
every query parameter. Any 200 response whose body contains an identifier
belonging to someone other than the caller is a leak.

No assumption is made about field names or resource types: the check matches
identifier *values*, so it covers records, user objects and any future resource
whose ids live in the database. Staff behaviour is not asserted either way;
staff-only routes simply return 403 to a member and are skipped.
"""

from __future__ import annotations

from itertools import product
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.main import app
from app.models import Record, User, UserRole
from tests.conftest import MEMBER_EMAIL, OTHER_MEMBER_EMAIL
from tests.utils.user import seed_user_token_headers

# Routes allowed to return other users' identifiers to a member, with the reason.
# Keep this empty unless a route is designed to do so.
EXEMPT_ROUTES: dict[str, str] = {}

SEEDED_MEMBER_EMAILS = (MEMBER_EMAIL, OTHER_MEMBER_EMAIL)


def identifiers_owned_by(db: Session, user: User) -> set[str]:
    """The user's own id plus the id of every record they own."""
    records = db.exec(select(Record.id).where(Record.user_id == user.id)).all()
    return {str(user.id), *(str(rid) for rid in records)}


def string_values(payload: Any) -> set[str]:
    """Every string value anywhere in a JSON payload."""
    if isinstance(payload, str):
        return {payload}
    if isinstance(payload, dict):
        return set().union(*(string_values(v) for v in payload.values()))
    if isinstance(payload, list):
        return set().union(*(string_values(v) for v in payload))
    return set()


def authenticated_get_routes() -> list[tuple[str, list[str], list[str]]]:
    """(path, path_param_names, query_param_names) for each authenticated GET route."""
    prefix = f"{settings.API_V1_STR}/"
    routes = []
    for path, methods in app.openapi()["paths"].items():
        spec = methods.get("get")
        if spec is None or not path.startswith(prefix) or not spec.get("security"):
            continue
        params = spec.get("parameters", [])
        path_params = [p["name"] for p in params if p["in"] == "path"]
        query_params = [p["name"] for p in params if p["in"] == "query"]
        routes.append((path, path_params, query_params))
    return routes


def test_member_never_receives_another_users_identifiers(
    client: TestClient, db: Session
) -> None:
    routes = authenticated_get_routes()
    assert routes, "no authenticated GET routes discovered"

    members = db.exec(
        select(User).where(
            User.role == UserRole.member, User.email.in_(SEEDED_MEMBER_EMAILS)
        )
    ).all()
    assert len(members) >= 2, "fixtures need two member-role users"
    everyone = db.exec(select(User)).all()

    leaks: list[str] = []
    for caller in members:
        headers = seed_user_token_headers(client=client, email=caller.email)
        foreign = set().union(
            *(identifiers_owned_by(db, u) for u in everyone if u.id != caller.id)
        )
        assert foreign, "need at least one foreign identifier to probe with"

        for path, path_params, query_params in routes:
            if path in EXEMPT_ROUTES:
                continue
            combos = (
                product(sorted(foreign), repeat=len(path_params))
                if path_params
                else [()]
            )
            for combo in combos:
                url = path
                for name, value in zip(path_params, combo, strict=True):
                    url = url.replace("{" + name + "}", value)
                response = client.get(
                    url, params=dict.fromkeys(query_params, ""), headers=headers
                )
                if response.status_code != 200:
                    continue
                leaked = string_values(response.json()) & foreign
                if leaked:
                    leaks.append(f"{caller.email} GET {url} -> {sorted(leaked)}")

    assert leaks == [], "cross-user identifiers returned to a member:\n" + "\n".join(
        leaks
    )
