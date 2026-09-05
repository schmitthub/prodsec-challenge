from typing import Annotated

from fastapi.responses import JSONResponse

from app.api.policies.login import LoginPolicy
from app.authz import FromPolicy, PolicyRouter
from app.models import Token

# The OAuth2 credential exchange must be available without an existing bearer.
# nosemgrep: authz-public-router
router = PolicyRouter(tags=["auth"], protected_policy=LoginPolicy)


@router.post("/login", response_model=Token)
def login_access_token(
    result: Annotated[Token | JSONResponse, FromPolicy(LoginPolicy.credentials)],
) -> Token | JSONResponse:
    return result
