from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import PUBLIC, PolicyRouter, SessionDep
from app.core import security
from app.core.config import settings
from app.models import Token

router = PolicyRouter(tags=["auth"])

# RFC 6749 §5.1 / §5.2: responses that carry or concern tokens must not be cached.
NO_STORE_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache"}


@router.post(
    "/login",
    dependencies=[PUBLIC],
    response_model=Token,
    responses={
        400: {
            "description": "Invalid grant (RFC 6749 §5.2)",
            "content": {"application/json": {"example": {"error": "invalid_grant"}}},
        }
    },
)
def login_access_token(
    session: SessionDep,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token | JSONResponse:
    """OAuth2 password-grant token endpoint (RFC 6749 §4.3).

    ``username`` carries the account email. Request body is
    ``application/x-www-form-urlencoded`` as the spec requires; JSON is not
    accepted.
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_grant",
                "error_description": "Invalid email or password",
            },
            headers=NO_STORE_HEADERS,
        )
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    response.headers.update(NO_STORE_HEADERS)
    return Token(
        access_token=security.create_access_token(user.id, expires_delta=expires),
        expires_in=int(expires.total_seconds()),
    )
