from app.authz import PUBLIC, Binding, Policy
from app.models import HealthStatus


def health_status() -> HealthStatus:
    return HealthStatus()


class HealthPolicy(Policy):
    # Liveness is deliberately anonymous and exposes no application data.
    principal = PUBLIC  # nosemgrep: authz-public-policy
    status = Binding((HealthStatus,), health_status)
