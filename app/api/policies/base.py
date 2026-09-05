from collections.abc import Callable
from typing import Any, ClassVar

from app.api.deps import get_current_user
from app.authz import Policy


class AuthenticatedPolicy(Policy):
    """Repository default: resolve the bearer to a real current User."""

    principal: ClassVar[Callable[..., Any]] = staticmethod(get_current_user)
