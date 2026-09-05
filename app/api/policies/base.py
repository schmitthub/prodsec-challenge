from typing import ClassVar

from app.api.deps import get_current_user
from app.authz import Policy, Principal


class AuthenticatedPolicy(Policy):
    """Repository default: resolve the bearer to a real current User."""

    principal: ClassVar[Principal] = staticmethod(get_current_user)
