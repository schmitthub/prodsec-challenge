from app.api.deps import CurrentUser
from app.api.policies.base import AuthenticatedPolicy
from app.authz import Binding
from app.models import User


def current_user(current_user: CurrentUser) -> User:
    return current_user


class UserPolicy(AuthenticatedPolicy):
    me = Binding((User,), current_user)
