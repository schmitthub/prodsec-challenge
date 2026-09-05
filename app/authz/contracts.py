"""Symbolic authorization contracts. No application models or database imports.

Providers are reviewed application code. This module checks their declaration
and wiring; it does not try to prove their business authorization logic.
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar

from fastapi import params

T = TypeVar("T")


class PolicyError(TypeError):
    """An incomplete or inconsistent authorization declaration."""


class Public:
    """Explicit anonymous access; scanner policy requires a justified exception."""


PUBLIC = Public()
Principal: TypeAlias = Callable[..., object] | Public | None


@dataclass(frozen=True, eq=False)
class Binding(Generic[T]):
    """Named protected resources and the trusted provider that authorizes them.

    Multiple resources describe a composite provider, not permission to fetch
    arbitrary instances of those types. Providers own the actual checks.
    A resource may name a shared base or domain marker; it does not constrain
    the provider's result or HTTP schema. Inheritance never grants access.
    """

    resources: tuple[type[Any], ...]
    provider: Callable[..., T]

    def __post_init__(self) -> None:
        if not self.resources or not all(isinstance(t, type) for t in self.resources):
            raise PolicyError("a binding requires protected resource types")
        if not callable(self.provider):
            raise PolicyError("a binding requires a callable provider")


class Policy:
    """Subclass in the application; declare principal and named Binding members.

    Authentication is mandatory unless principal is explicitly PUBLIC. GET/HEAD
    are the default supported operations; other methods require a deliberate
    policy declaration. No role, key type, ORM, or ownership rule lives here.
    """

    principal: ClassVar[Principal] = None
    methods: ClassVar[frozenset[str]] = frozenset({"GET", "HEAD"})

    @classmethod
    def bindings(cls) -> dict[str, Binding[Any]]:
        return {
            name: value
            for name, value in inspect.getmembers(cls)
            if isinstance(value, Binding)
        }

    @classmethod
    def validate(cls) -> None:
        if cls.principal is not PUBLIC and not callable(cls.principal):
            raise PolicyError(f"{cls.__name__}: declare a principal or PUBLIC")
        if not cls.bindings():
            raise PolicyError(f"{cls.__name__}: declare at least one resource binding")
        if not cls.methods or not cls.methods <= {
            "GET",
            "HEAD",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
            "TRACE",
        }:
            raise PolicyError(f"{cls.__name__}: invalid HTTP methods")


class FromPolicy(params.Depends):
    """A normal FastAPI dependency with a checkable policy binding attached."""

    binding: Binding[Any]

    def __init__(self, binding: Binding[Any]) -> None:
        if not isinstance(binding, Binding):
            raise PolicyError("FromPolicy requires a Binding symbol")
        super().__init__(dependency=binding.provider)
        object.__setattr__(self, "binding", binding)


class _PolicyOverride(params.Depends):
    policy: type[Policy]

    def __init__(self, policy: type[Policy]) -> None:
        super().__init__()
        object.__setattr__(self, "policy", policy)


def use_policy(policy: type[Policy]) -> params.Depends:
    """Explicit endpoint override, always flagged by the repository's scanner."""
    return _PolicyOverride(policy)
