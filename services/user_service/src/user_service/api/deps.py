from fastapi import Request

from user_service.application.services import UserApplicationService
from user_service.infrastructure.cache.user_cache import RedisUserCache
from user_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_user_service(request: Request) -> UserApplicationService:
    uow = SqlAlchemyUnitOfWork(request.app.state.db_session_factory)
    cache = RedisUserCache(request.app.state.redis)
    return UserApplicationService(uow, cache)
