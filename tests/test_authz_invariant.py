"""Cross-user identifier invariant: a member never receives another user's identifiers.

Walks every authenticated GET route in the app's OpenAPI schema and calls it as
each member-role user, substituting other users' identifiers (their user id and
the ids of records they own) into path parameters and an empty value into every
query parameter. Any 200 response whose body contains an identifier belonging to
someone other than the caller is a leak.

No assumption is made about field names or resource types: the check matches
identifier *values*, so it covers records, user objects and any future resource
whose ids come from the fixtures. Staff behaviour is not asserted either way;
staff-only routes simply return 403 to a member and are skipped.
"""

from __future__ import annotations

import unittest
from itertools import product
from typing import Any

from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)

# Routes allowed to return other users' identifiers to a member, with the reason.
# Keep this empty unless a route is designed to do so.
EXEMPT_ROUTES: dict[str, str] = {}


def login(email: str, password: str) -> str:
    response = client.post("/api/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def identifiers_owned_by(user_id: str) -> set[str]:
    """The user's own id plus the id of every record they own."""
    owned = {user_id}
    owned.update(
        rid for rid, rec in db.RECORDS.items() if rec["owner_user_id"] == user_id
    )
    return owned


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
    """(path, path_param_names, query_param_names) for each GET route under /api."""
    routes = []
    for path, methods in app.openapi()["paths"].items():
        spec = methods.get("get")
        if spec is None or not path.startswith("/api/") or not spec.get("security"):
            continue
        params = spec.get("parameters", [])
        path_params = [p["name"] for p in params if p["in"] == "path"]
        query_params = [p["name"] for p in params if p["in"] == "query"]
        routes.append((path, path_params, query_params))
    return routes


class CrossUserIdentifierInvariant(unittest.TestCase):
    def test_member_never_receives_another_users_identifiers(self):
        members = [u for u in db.USERS.values() if u["role"] == "member"]
        self.assertGreaterEqual(len(members), 2, "fixtures need two member-role users")

        leaks: list[str] = []
        for caller in members:
            headers = {
                "Authorization": f"Bearer {login(caller['email'], caller['password'])}"
            }
            foreign = set().union(
                *(identifiers_owned_by(uid) for uid in db.USERS if uid != caller["id"])
            )

            for path, path_params, query_params in authenticated_get_routes():
                if path in EXEMPT_ROUTES:
                    continue
                combos = (
                    product(sorted(foreign), repeat=len(path_params))
                    if path_params
                    else [()]
                )
                for combo in combos:
                    url = path
                    for name, value in zip(path_params, combo):
                        url = url.replace("{" + name + "}", value)
                    response = client.get(
                        url, params=dict.fromkeys(query_params, ""), headers=headers
                    )
                    if response.status_code != 200:
                        continue
                    leaked = string_values(response.json()) & foreign
                    if leaked:
                        leaks.append(f"{caller['id']} GET {url} -> {sorted(leaked)}")

        self.assertEqual(
            leaks,
            [],
            "cross-user identifiers returned to a member:\n" + "\n".join(leaks),
        )


if __name__ == "__main__":
    unittest.main()
