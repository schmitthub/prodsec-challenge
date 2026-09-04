import requests
from fastapi import HTTPException, status
from pydantic import HttpUrl

from app.api.deps import PolicyRouter, require
from app.core.config import settings
from app.models import PreviewRequest, Scope

router = PolicyRouter(tags=["webhooks"])

FETCH_TIMEOUT_SECONDS = 2


class DisallowedUrlError(ValueError):
    """The URL's scheme or host is outside WEBHOOK_ALLOWED_HOSTS."""


def _check_allowed(url: HttpUrl) -> None:
    """https only; host must be an exact, case-insensitive allowlist member."""
    host = (url.host or "").lower()
    if url.scheme != "https" or host not in settings.webhook_allowed_hosts:
        raise DisallowedUrlError(f"host {host!r} is not in the egress allowlist")


def _fetch_allowed(url: HttpUrl) -> requests.Response:
    """GET ``url`` after the allowlist check. Redirects are not followed, so a
    3xx from an allowed host cannot steer the fetch to a host outside the list."""
    _check_allowed(url)
    return requests.get(str(url), timeout=FETCH_TIMEOUT_SECONDS, allow_redirects=False)


@router.post("/webhooks/vendor-preview", dependencies=[require(Scope.webhooks_preview)])
def preview_vendor_webhook(request: PreviewRequest):
    try:
        response = _fetch_allowed(request.callback_url)
    except DisallowedUrlError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="callback_url host is not allowed",
        )
    except requests.RequestException as e:
        return {
            "status_code": 500,
            "content_type": None,
            "preview": str(e),
        }
    return {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "preview": response.text[:200],
    }
