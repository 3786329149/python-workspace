from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import EmailStr

from user_service.api.deps import (
    get_current_user_id,
    get_user_service,
    require_internal_token,
)
from user_service.api.v1.schemas import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from user_service.application.commands import (
    CreateUserCommand,
    UpdateUserProfileCommand,
    UserIdCommand,
)
from user_service.application.services import UserApplicationService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.create_user(CreateUserCommand(**payload.model_dump()))
    return UserResponse.from_domain(user)


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(require_internal_token)],
)
async def get_current_user(
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(current_user_id)
    return UserResponse.from_domain(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(
    email: EmailStr,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user_by_email(str(email))
    return UserResponse.from_domain(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    return UserResponse.from_domain(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    changes = payload.model_dump(exclude_unset=True)
    user = await service.update_user_profile(
        UpdateUserProfileCommand(user_id=user_id, changes=changes)
    )
    return UserResponse.from_domain(user)


@router.post("/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.disable_user(UserIdCommand(user_id=user_id))
    return UserResponse.from_domain(user)


@router.post("/{user_id}/enable", response_model=UserResponse)
async def enable_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.enable_user(UserIdCommand(user_id=user_id))
    return UserResponse.from_domain(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> Response:
    await service.delete_user(UserIdCommand(user_id=user_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
