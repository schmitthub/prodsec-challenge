"""FastAPI wiring for declared policies, using ordinary dependency injection."""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, cast, get_args, get_origin, get_type_hints

from fastapi import APIRouter, Depends, params

from .contracts import PUBLIC, Binding, FromPolicy, Policy, PolicyError, _PolicyOverride


@dataclass(frozen=True)
class RouteContract:
    policy: type[Policy]
    bindings: tuple[Binding[Any], ...]
    overridden: bool


class PolicyRouter(APIRouter):
    """Every route selects and actually executes registered policy providers.

    FastAPI owns signature interpretation and dependency execution. We neither
    rewrite endpoint functions nor infer business permissions from response DTOs.
    """

    def __init__(self, *, protected_policy: type[Policy], **kwargs: Any):
        self._validate_policy(protected_policy)
        self.protected_policy = protected_policy
        if kwargs.get("dependencies"):
            raise PolicyError("declare dependencies in policy providers")
        super().__init__(**kwargs)

    @staticmethod
    def _validate_policy(policy: type[Policy]) -> None:
        if not isinstance(policy, type) or not issubclass(policy, Policy):
            raise PolicyError("protected_policy must name a Policy subclass")
        policy.validate()

    def add_api_route(
        self, path: str, endpoint: Callable[..., Any], **kwargs: Any
    ) -> None:
        dependencies = list(kwargs.get("dependencies") or ())
        overrides = [d for d in dependencies if isinstance(d, _PolicyOverride)]
        if len(overrides) > 1 or len(overrides) != len(dependencies):
            raise PolicyError("endpoint dependencies may only declare one use_policy")
        policy = overrides[0].policy if overrides else self.protected_policy
        self._validate_policy(policy)
        methods = set(kwargs.get("methods") or {"GET"})
        if not methods <= policy.methods:
            raise PolicyError(f"{policy.__name__}: unsupported HTTP method {methods}")

        allowed = tuple(policy.bindings().values())
        bindings: list[Binding[Any]] = []
        hints = get_type_hints(endpoint, include_extras=True)
        for name, parameter in inspect.signature(endpoint).parameters.items():
            annotation = hints.get(name, parameter.annotation)
            metadata = (
                get_args(annotation)[1:] if get_origin(annotation) is Annotated else ()
            )
            for item in (*metadata, parameter.default):
                if isinstance(item, FromPolicy):
                    if item.binding not in allowed:
                        raise PolicyError(
                            f"{name}: binding does not belong to {policy.__name__}"
                        )
                    if item.binding not in bindings:
                        bindings.append(item.binding)
                elif isinstance(item, params.Depends):
                    raise PolicyError(
                        f"{name}: use FromPolicy; raw dependencies belong in providers"
                    )
        if not bindings:
            raise PolicyError(f"{path}: consume a declared binding with FromPolicy")

        kwargs["dependencies"] = (
            []
            if policy.principal is PUBLIC
            else [Depends(cast(Callable[..., Any], policy.principal))]
        )
        super().add_api_route(path, endpoint, **kwargs)
        # Metadata belongs to this registration, never the shared endpoint.
        self.routes[-1].__dict__["authz_contract"] = RouteContract(
            policy, tuple(bindings), bool(overrides)
        )
