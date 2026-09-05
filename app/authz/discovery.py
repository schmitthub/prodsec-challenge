"""Discover live contracts, including hidden routes and nested router includes.

FastAPI 0.141's lazy include traversal is isolated here. Compatibility is tested
against the locked version; no generated endpoint inventory is maintained.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, _EffectiveRouteContext, _IncludedRouter
from starlette.routing import Mount, Route

from .contracts import PUBLIC, Policy, PolicyError
from .router import RouteContract


@dataclass(frozen=True)
class MountedContract:
    method: str
    path: str
    contract: RouteContract

    @property
    def policy(self) -> type[Policy]:
        return self.contract.policy

    @property
    def public(self) -> bool:
        return self.policy.principal is PUBLIC

    @property
    def overridden(self) -> bool:
        return self.contract.overridden

    @property
    def resources(self) -> tuple[type[Any], ...]:
        return tuple(
            dict.fromkeys(t for b in self.contract.bindings for t in b.resources)
        )


def _walk(routes: list[Any]) -> Iterator[Any]:
    for route in routes:
        if isinstance(route, _IncludedRouter):
            yield from _walk(route.effective_candidates())
        else:
            yield route


def _calls(dependant: Dependant) -> list[Any]:
    return [
        dependant.call,
        *(call for dep in dependant.dependencies for call in _calls(dep)),
    ]


def discover_contracts(app: FastAPI) -> list[MountedContract]:
    """Validate all mounted HTTP operations and return their live declarations.

    Only FastAPI's own documentation routes are excluded. Unknown raw routes,
    mounted subapplications, and websockets fail closed rather than disappearing.
    """
    documentation = {
        app.openapi_url,
        app.docs_url,
        app.redoc_url,
        app.swagger_ui_oauth2_redirect_url,
    }
    contracts: list[MountedContract] = []
    for route in _walk(app.routes):
        original = (
            route.original_route if isinstance(route, _EffectiveRouteContext) else route
        )
        if not isinstance(original, APIRoute):
            if (
                isinstance(original, Route)
                and not isinstance(original, Mount)
                and route.path in documentation
                and original.endpoint.__module__ == "fastapi.applications"
            ):
                continue
            raise PolicyError(f"{route.path}: unsupported or unprotected mounted route")
        contract = getattr(original, "authz_contract", None)
        if not isinstance(contract, RouteContract):
            raise PolicyError(f"{route.path}: missing policy contract")
        calls = _calls(route.dependant)
        required = [b.provider for b in contract.bindings]
        if contract.policy.principal is not PUBLIC:
            required.append(cast(Callable[..., Any], contract.policy.principal))
        if any(provider not in calls for provider in required):
            raise PolicyError(f"{route.path}: declared policy is not wired")
        for method in sorted(route.methods or ()):
            contracts.append(MountedContract(method, route.path, contract))
    return sorted(contracts, key=lambda c: (c.path, c.method))
