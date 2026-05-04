from fastapi import Header, HTTPException, Request, status
from auth_service.application.services import AuthApplicationService
from auth_service.infrastructure.db.unit_of_work import SqlAlchemyAuthUnitOfWork
from auth_service.infrastructure.http_user_profiles import HttpUserProfileClient
from auth_service.config import settings

def get_auth_service(request: Request) -> AuthApplicationService:
    uow = SqlAlchemyAuthUnitOfWork(request.app.state.db_session_factory)
    user_profiles = HttpUserProfileClient(
        request.app.state.http_client,
        settings.USER_SERVICE_URL,
        settings.INTERNAL_API_TOKEN,
    )
    return AuthApplicationService(
        uow,
        user_profiles,
        request.app.state.redis,
        jwt_secret_key=settings.JWT_SECRET_KEY,
        jwt_algorithm=settings.JWT_ALGORITHM,
        access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    if not settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="internal api token is not configured",
        )
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid internal api token",
        )
