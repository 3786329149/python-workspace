from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import EmailStr

from user_service.api.deps import (
    get_current_user_id,
    get_user_service,
    require_internal_token,
    require_permission,
)
from user_service.api.v1.schemas import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    UserAdminUpdateRequest,
)
from user_service.application.commands import (
    CreateUserCommand,
    UpdateUserProfileCommand,
    UpdateUserAdminCommand,
    UserIdCommand,
)
from user_service.application.services import UserApplicationService

router = APIRouter(prefix="/users", tags=["users"])


async def _make_user_response(user: User, service: UserApplicationService) -> UserResponse:
    roles = await service.get_user_role_keys(user.id)
    perms = await service.get_user_permissions(user.id)
    return UserResponse.from_domain(user, roles=roles, permissions=perms)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user:create"))],
)
async def create_user(
    payload: UserCreateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.create_user(CreateUserCommand(**payload.model_dump()))
    return await _make_user_response(user, service)

@router.get(
    "",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission("user:list"))],
)
async def list_users(
    tenant_id: UUID | None = None,
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> list[UserResponse]:
    users = await service.get_all_users(tenant_id, current_user_id=current_user_id)
    return [await _make_user_response(u, service) for u in users]


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
    if user.tenant_id:
        from user_service.infrastructure.db.context import set_current_tenant
        set_current_tenant(user.tenant_id)
    return await _make_user_response(user, service)


@router.get(
    "/by-email/{email}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:list"))],
)
async def get_user_by_email(
    email: EmailStr,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user_by_email(str(email))
    return await _make_user_response(user, service)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:list"))],
)
async def get_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    return await _make_user_response(user, service)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:edit"))],
)
async def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    changes = payload.model_dump(exclude_unset=True)
    user = await service.update_user_profile(
        UpdateUserProfileCommand(user_id=user_id, changes=changes)
    )
    return await _make_user_response(user, service)

@router.patch(
    "/{user_id}/admin",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:edit"))],
)
async def update_user_admin(
    user_id: UUID,
    payload: UserAdminUpdateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.update_user_admin(
        UpdateUserAdminCommand(
            user_id=user_id,
            **payload.model_dump(exclude_unset=True)
        )
    )
    return await _make_user_response(user, service)


@router.post(
    "/{user_id}/disable",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:edit"))],
)
async def disable_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.disable_user(UserIdCommand(user_id=user_id))
    return await _make_user_response(user, service)


@router.post(
    "/{user_id}/enable",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:edit"))],
)
async def enable_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> UserResponse:
    user = await service.enable_user(UserIdCommand(user_id=user_id))
    return await _make_user_response(user, service)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:delete"))],
)
async def delete_user(
    user_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> Response:
    await service.delete_user(UserIdCommand(user_id=user_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
