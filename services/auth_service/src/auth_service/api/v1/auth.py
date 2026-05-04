from fastapi import APIRouter, Depends, Request, status

from auth_service.api.deps import get_auth_service, require_internal_token
from auth_service.application.services import AuthApplicationService
from auth_service.application.commands import (
    BindPasswordCommand,
    LoginCommand,
    RefreshTokenCommand,
    RegisterCommand,
)
from auth_service.api.v1.schemas import (
    AuthBindResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    LogoutRequest,
    LogoutAllRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthApplicationService = Depends(get_auth_service),
) -> RegisterResponse:
    idempotency_key = request.headers.get("Idempotency-Key")
    data = await service.register(
        RegisterCommand(**payload.model_dump()),
        request_id=getattr(request.state, "request_id", None),
        idempotency_key=idempotency_key,
    )
    return RegisterResponse(**data)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: AuthApplicationService = Depends(get_auth_service),
) -> TokenResponse:
    data = await service.login(LoginCommand(**payload.model_dump()))
    return TokenResponse(**data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthApplicationService = Depends(get_auth_service),
) -> TokenResponse:
    data = await service.refresh(RefreshTokenCommand(**payload.model_dump()))
    return TokenResponse(**data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    service: AuthApplicationService = Depends(get_auth_service),
) -> None:
    await service.logout(payload.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    payload: LogoutAllRequest,
    service: AuthApplicationService = Depends(get_auth_service),
) -> None:
    await service.logout_all(payload.user_id)


@router.post(
    "/bind-password",
    response_model=AuthBindResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_internal_token)],
)
async def bind_password(
    command: BindPasswordCommand,
    service: AuthApplicationService = Depends(get_auth_service),
) -> AuthBindResponse:
    auth = await service.bind_password(command)
    return AuthBindResponse.from_domain(auth)
