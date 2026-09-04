"""Declared access policy of every mounted route, read back from the app.

``PolicyRouter`` enforces declarations at import; this module makes them
inspectable after the fact so tests can (1) assert every route resolves to
exactly one policy, (2) diff the whole table against the checked-in
``policy.json`` so a policy change is visible in review, and (3) derive the
expected status for every principal x route and compare with observed
behaviour.

Regenerate the snapshot after an intentional change::

    uv run python -m app.api.policy

FastAPI 0.140+ includes routers lazily (``_IncludedRouter``), so the flat
``app.routes`` no longer lists API routes; ``effective_routes`` walks the
private effective-route tree. The walker test fails loudly if that API moves.
"""

import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, _EffectiveRouteContext, _IncludedRouter

from app.api.deps import RowAccess, _anonymous, get_current_user
from app.core.config import settings

SNAPSHOT = Path(__file__).with_name("policy.json")


@dataclass(frozen=True)
class RoutePolicy:
    method: str
    path: str
    public: bool
    identity: bool
    scopes: tuple[str, ...]
    rows: tuple[RowAccess, ...]

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"

    def as_json(self) -> dict[str, Any] | str:
        if self.public:
            return "PUBLIC"
        return {
            "scopes": list(self.scopes),
            "rows": [row.label for row in self.rows],
        }


def effective_routes(app: FastAPI) -> Iterator[tuple[str, str, Dependant]]:
    """``(method, path, dependant)`` for every API route as actually mounted."""

    def walk(routes: list[Any]) -> Iterator[Any]:
        for route in routes:
            if isinstance(route, _IncludedRouter):
                yield from walk(route.effective_candidates())
            elif isinstance(route, _EffectiveRouteContext | APIRoute):
                yield route

    for route in walk(app.routes):
        if isinstance(route, _EffectiveRouteContext) and not isinstance(
            route.original_route, APIRoute
        ):
            continue
        for method in sorted(route.methods or ()):
            yield method, route.path, route.dependant


def _collect(
    dependant: Dependant,
    scopes: set[str],
    rows: list[RowAccess],
    flags: dict[str, bool],
) -> None:
    call = dependant.call
    if call is _anonymous:
        flags["public"] = True
    if call is get_current_user:
        flags["identity"] = True
    scopes.update(dependant.own_oauth_scopes or ())
    row = getattr(call, "__row_access__", None)
    if isinstance(row, RowAccess) and row not in rows:
        rows.append(row)
    for sub in dependant.dependencies:
        _collect(sub, scopes, rows, flags)


def route_policy(method: str, path: str, dependant: Dependant) -> RoutePolicy:
    scopes: set[str] = set()
    rows: list[RowAccess] = []
    flags = {"public": False, "identity": False}
    _collect(dependant, scopes, rows, flags)
    return RoutePolicy(
        method=method,
        path=path,
        public=flags["public"],
        identity=flags["identity"],
        scopes=tuple(sorted(scopes)),
        rows=tuple(rows),
    )


def route_policies(app: FastAPI) -> list[RoutePolicy]:
    """Every mounted route, API and otherwise, sorted by ``METHOD path``."""
    policies = [route_policy(m, p, d) for m, p, d in effective_routes(app)]
    return sorted(policies, key=lambda p: p.key)


def api_policies(app: FastAPI) -> list[RoutePolicy]:
    """Routes under ``settings.API_V1_STR``: the ones PolicyRouter governs."""
    prefix = f"{settings.API_V1_STR}/"
    return [p for p in route_policies(app) if p.path.startswith(prefix)]


def policy_table(app: FastAPI) -> dict[str, Any]:
    return {p.key: p.as_json() for p in api_policies(app)}


def main() -> int:
    from app.main import app

    SNAPSHOT.write_text(json.dumps(policy_table(app), indent=2) + "\n")
    print(f"wrote {SNAPSHOT}")  # noqa: T201 - CLI output
    return 0


if __name__ == "__main__":
    sys.exit(main())
