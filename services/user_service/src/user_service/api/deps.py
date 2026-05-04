from typing import Callable
from uuid import UUID

from fastapi import Depends, Header, Request

from user_service.application.services import UserApplicationService
from user_service.config import settings
from user_service.domain.errors import (
    UserContextInvalid,
    UserContextRequired,
    UserInternalAuthFailed,
    UserPermissionDenied,
)
from user_service.infrastructure.cache.user_cache import RedisUserCache
from user_service.infrastructure.db.context import set_current_tenant
from user_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_user_service(request: Request) -> UserApplicationService:
    uow = SqlAlchemyUnitOfWork(request.app.state.db_session_factory)
    cache = RedisUserCache(request.app.state.redis)
    return UserApplicationService(uow, cache)


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    if (
        not settings.INTERNAL_API_TOKEN
        or x_internal_token != settings.INTERNAL_API_TOKEN
    ):
        raise UserInternalAuthFailed()


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
) -> UUID:
    if not x_user_id:
        raise UserContextRequired()
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise UserContextInvalid() from exc


def require_permission(permission: str) -> Callable:
    """Dependency factory to enforce a specific permission."""

    async def _permission_dependency(
        user_id: UUID = Depends(get_current_user_id),
        service: UserApplicationService = Depends(get_user_service),
    ) -> None:
        # Set tenant context for the duration of this request
        user = await service.get_user(user_id)
        if user.tenant_id:
            set_current_tenant(user.tenant_id)
            
        perms = await service.get_user_permissions(user_id)
        if permission not in perms:
            raise UserPermissionDenied(f"Permission '{permission}' is required")

    return _permission_dependency
