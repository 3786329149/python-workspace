from dataclasses import dataclass

from gateway.config import settings


@dataclass(frozen=True, slots=True)
class ServiceRoute:
    name: str
    base_url: str
    upstream_prefix: str


AUTH_ROUTE = ServiceRoute(
    name="auth-service",
    base_url=settings.AUTH_SERVICE_URL,
    upstream_prefix="/api/v1/auth",
)
