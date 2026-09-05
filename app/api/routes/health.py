from typing import Annotated

from app.api.policies.health import HealthPolicy
from app.authz import FromPolicy, PolicyRouter
from app.models import HealthStatus

# Liveness has no user-specific data and is needed by infrastructure probes.
# nosemgrep: authz-public-router
router = PolicyRouter(tags=["health"], protected_policy=HealthPolicy)


@router.get("/health")
def health(
    result: Annotated[HealthStatus, FromPolicy(HealthPolicy.status)],
) -> HealthStatus:
    return result
