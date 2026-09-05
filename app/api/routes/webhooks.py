from typing import Annotated

from app.api.policies.webhooks import VendorPreviewPolicy
from app.authz import FromPolicy, PolicyRouter
from app.models import VendorPreview

router = PolicyRouter(tags=["webhooks"], protected_policy=VendorPreviewPolicy)


@router.post("/webhooks/vendor-preview", response_model=VendorPreview)
def preview_vendor_webhook(
    result: Annotated[VendorPreview, FromPolicy(VendorPreviewPolicy.preview)],
) -> VendorPreview:
    return result
