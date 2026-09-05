from typing import ClassVar

from app.authz import PUBLIC, Binding, Policy, Principal
from app.models import HealthStatus


def health_status() -> HealthStatus:
    return HealthStatus()


class HealthPolicy(Policy):
    # Liveness is deliberately anonymous and exposes no application data.
    principal: ClassVar[Principal] = PUBLIC  # nosemgrep: authz-public-policy
    status = Binding((HealthStatus,), health_status)
