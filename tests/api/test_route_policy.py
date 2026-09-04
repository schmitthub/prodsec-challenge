"""Every mounted API route resolves to exactly one declared policy, escape
hatches are allowlisted with a reason, and the whole table matches the
checked-in snapshot so a policy change is visible in review.

No database: these read the mounted app's dependency trees only.
"""

import json

from app.api.policy import SNAPSHOT, api_policies, policy_table, route_policies
from app.core.config import settings
from app.main import app

# Routes that opt out of identity, with the reason. A PUBLIC route missing here
# fails; a stale entry fails too.
PUBLIC_ROUTES: dict[str, str] = {
    f"POST {settings.API_V1_STR}/login": "OAuth2 password-grant token endpoint",
}

# Routes mounted outside the API prefix. Not governed by PolicyRouter; anything
# new here needs a deliberate decision.
NON_API_ROUTES: set[str] = {"GET /health"}


def test_walker_sees_the_api() -> None:
    keys = {p.key for p in api_policies(app)}
    assert f"GET {settings.API_V1_STR}/records" in keys, keys


def test_every_api_route_has_exactly_one_policy() -> None:
    bad = [
        p.key for p in api_policies(app) if p.public == p.identity
    ]  # neither, or both
    assert not bad, f"routes without exactly one of PUBLIC/identity: {bad}"


def test_public_routes_are_allowlisted_with_a_reason() -> None:
    public = {p.key for p in api_policies(app) if p.public}
    assert public == set(PUBLIC_ROUTES), (
        f"PUBLIC routes {sorted(public)} != allowlist {sorted(PUBLIC_ROUTES)}"
    )
    assert all(PUBLIC_ROUTES.values()), "every PUBLIC route needs a reason"


def test_row_loaders_require_a_scope() -> None:
    for p in api_policies(app):
        if p.rows:
            assert p.scopes, f"{p.key} loads rows but requires no scope"


def test_non_api_routes_are_known() -> None:
    prefix = f"{settings.API_V1_STR}/"
    outside = {p.key for p in route_policies(app) if not p.path.startswith(prefix)}
    assert outside == NON_API_ROUTES, outside


def test_policy_snapshot_matches() -> None:
    expected = json.loads(SNAPSHOT.read_text())
    assert policy_table(app) == expected, (
        "declared route policy changed; review the diff, then regenerate with "
        "`uv run python -m app.api.policy`"
    )
