from fastapi import APIRouter, Depends, HTTPException, status
from auth_service.api.deps import get_auth_service
from auth_service.application.services import AuthApplicationService
from auth_service.application.commands import BindPasswordCommand
from auth_service.api.v1.schemas import AuthBindResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/bind-password", response_model=AuthBindResponse, status_code=status.HTTP_201_CREATED)
async def bind_password(
    command: BindPasswordCommand,
    service: AuthApplicationService = Depends(get_auth_service),
) -> AuthBindResponse:
    try:
        auth = await service.bind_password(command)
        return AuthBindResponse.from_domain(auth)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
