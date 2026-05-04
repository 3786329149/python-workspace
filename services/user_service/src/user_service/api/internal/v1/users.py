from uuid import UUID

from fastapi import APIRouter, Depends, status

from user_service.api.deps import get_user_service, require_internal_token
from user_service.api.internal.v1.schemas import RegistrationProfileRequest
from user_service.api.v1.schemas import UserResponse
from user_service.application.commands import (
    CreateRegistrationProfileCommand,
    UserIdCommand,
)
from user_service.application.services import UserApplicationService

router = APIRouter(
    prefix="/users",
    tags=["internal users"],
    dependencies=[Depends(require_internal_token)],
)

@router.post("/registration-profile", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_registration_profile(
    request: RegistrationProfileRequest,
    user_service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    command = CreateRegistrationProfileCommand(
        email=request.email,
        username=request.username,
    )
    user = await user_service.create_registration_profile(command)
    return UserResponse.from_domain(user)

@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    user_service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    command = UserIdCommand(user_id=user_id)
    user = await user_service.activate_user(command)
    return UserResponse.from_domain(user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    user_service: UserApplicationService = Depends(get_user_service),
) -> None:
    command = UserIdCommand(user_id=user_id)
    await user_service.delete_user(command)
