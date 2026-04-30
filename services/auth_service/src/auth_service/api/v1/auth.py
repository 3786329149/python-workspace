from fastapi import APIRouter, Depends, Request, status

from auth_service.api.deps import get_auth_service, require_internal_token
from auth_service.application.services import AuthApplicationService
from auth_service.application.commands import BindPasswordCommand, RegisterCommand
from auth_service.api.v1.schemas import (
    AuthBindResponse,
    RegisterRequest,
    RegisterResponse,
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
    data = await service.register(
        RegisterCommand(**payload.model_dump()),
        request_id=getattr(request.state, "request_id", None),
    )
    return RegisterResponse(**data)


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
