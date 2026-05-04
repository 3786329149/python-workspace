from dataclasses import dataclass
from typing import Sequence

from gateway.config import settings


@dataclass(frozen=True, slots=True)
class ServiceRoute:
    name: str
    base_url: str
    upstream_prefix: str
    requires_internal_token: bool = False
    # Optional permission key that the authenticated user must hold.
    # e.g. "user:list"  None means no permission check beyond authentication.
    requires_permission: str | None = None


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
    requires_permission="user:list",
)


ROLE_ROUTE = ServiceRoute(
    name="user-service",
    base_url=settings.USER_SERVICE_URL,
    upstream_prefix="/api/v1/roles",
    requires_internal_token=True,
    requires_permission="role:list",
)


MENU_ROUTE = ServiceRoute(
    name="user-service",
    base_url=settings.USER_SERVICE_URL,
    upstream_prefix="/api/v1/menus",
    requires_internal_token=True,
    requires_permission="role:list",
)


DEPT_ROUTE = ServiceRoute(
    name="user-service",
    base_url=settings.USER_SERVICE_URL,
    upstream_prefix="/api/v1/depts",
    requires_internal_token=True,
    requires_permission="dept:list",
)
