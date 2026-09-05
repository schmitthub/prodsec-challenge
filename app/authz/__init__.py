"""Reusable FastAPI authorization contracts; application policy lives elsewhere."""

from .contracts import (
    PUBLIC,
    Binding,
    FromPolicy,
    Policy,
    PolicyError,
    Principal,
    use_policy,
)
from .discovery import MountedContract, discover_contracts
from .router import PolicyRouter

__all__ = [
    "PUBLIC",
    "Binding",
    "FromPolicy",
    "MountedContract",
    "Policy",
    "PolicyError",
    "PolicyRouter",
    "Principal",
    "discover_contracts",
    "use_policy",
]
