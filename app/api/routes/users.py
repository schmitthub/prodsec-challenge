from typing import Annotated

from app.api.policies.users import UserPolicy
from app.authz import FromPolicy, PolicyRouter
from app.models import User, UserPublic

router = PolicyRouter(tags=["users"], protected_policy=UserPolicy)


@router.get("/me", response_model=UserPublic)
def read_me(user: Annotated[User, FromPolicy(UserPolicy.me)]) -> User:
    return user
