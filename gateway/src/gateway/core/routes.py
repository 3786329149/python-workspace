from dataclasses import dataclass

from gateway.config import settings


@dataclass(frozen=True, slots=True)
class ServiceRoute:
    name: str
    base_url: str
    upstream_prefix: str
    requires_internal_token: bool = False


AUTH_ROUTE = ServiceRoute(
    name="auth-service",
    base_url=settings.AUTH_SERVICE_URL,
    upstream_prefix="/api/v1/auth",
)


USER_ROUTE = ServiceRoute(
    name="user-service",
    base_url=settings.USER_SERVICE_URL,
    upstream_prefix="/api/v1/users",
    requires_internal_token=True,
)
