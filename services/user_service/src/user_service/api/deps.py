from uuid import UUID

from fastapi import Header, Request

from user_service.application.services import UserApplicationService
from user_service.config import settings
from user_service.domain.errors import (
    UserContextInvalid,
    UserContextRequired,
    UserInternalAuthFailed,
)
from user_service.infrastructure.cache.user_cache import RedisUserCache
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
