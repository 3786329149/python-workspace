"""RBAC API endpoints — permissions query and role/menu management.

All endpoints require X-Internal-Token (supplied by the gateway).
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from user_service.api.deps import get_current_user_id, get_user_service, require_internal_token
from user_service.application.commands import (
    AssignMenuToRoleCommand,
    CreateRoleCommand,
)
from user_service.application.services import UserApplicationService
from user_service.domain.models import Role

router = APIRouter(
    prefix="/users",
    tags=["rbac"],
    dependencies=[Depends(require_internal_token)],
)

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class PermissionsResponse(BaseModel):
    user_id: UUID
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    role_id: UUID


class CreateRoleRequest(BaseModel):
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=50)
    role_key: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z_:]+$")
    data_scope: int = Field(default=1, ge=1, le=4)


class RoleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    role_key: str
    data_scope: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, role: Role) -> "RoleResponse":
        return cls(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            role_key=role.role_key,
            data_scope=role.data_scope,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )


class AssignMenuRequest(BaseModel):
    menu_id: UUID


# --------------------------------------------------------------------------- #
# Endpoints: current user's permissions
# --------------------------------------------------------------------------- #

@router.get(
    "/me/permissions",
    response_model=PermissionsResponse,
    summary="Get current user's permission keys",
)
async def get_my_permissions(
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> PermissionsResponse:
    """Return the permission keys (e.g. ``user:list``) for the calling user.

    Results are cached in Redis for 5 minutes
    (key: ``permission:user:{user_id}``).
    Cache is invalidated when a new role is assigned to the user.
    """
    perms = await service.get_user_permissions(current_user_id)
    return PermissionsResponse(user_id=current_user_id, permissions=perms)


# --------------------------------------------------------------------------- #
# Endpoints: assign role to a user
# --------------------------------------------------------------------------- #

@router.post(
    "/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Assign a role to a user",
)
async def assign_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    """Assign an existing role to a user.

    Automatically invalidates the user's permission cache so the next
    request to ``/me/permissions`` reflects the new role.
    """
    await service.assign_role_to_user(user_id, payload.role_id)


# --------------------------------------------------------------------------- #
# Endpoints: role management
# --------------------------------------------------------------------------- #

roles_router = APIRouter(
    prefix="/roles",
    tags=["rbac"],
    dependencies=[Depends(require_internal_token)],
)


@roles_router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
)
async def create_role(
    payload: CreateRoleRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> RoleResponse:
    """Create a role scoped to a tenant.

    ``role_key`` must be unique within the tenant (e.g. ``admin``, ``editor``).
    Returns 409 if the key already exists.
    """
    role = await service.create_role(
        CreateRoleCommand(
            tenant_id=payload.tenant_id,
            name=payload.name,
            role_key=payload.role_key,
            data_scope=payload.data_scope,
        )
    )
    return RoleResponse.from_domain(role)


@roles_router.post(
    "/{role_id}/permissions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Assign a menu/permission-point to a role",
)
async def assign_menu_to_role(
    role_id: UUID,
    payload: AssignMenuRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    """Bind a menu item (``menu_type=F``) to a role.

    Users holding this role will pick up the new permission on their next
    cache-refresh (within 5 minutes).
    """
    await service.assign_menu_to_role(
        AssignMenuToRoleCommand(role_id=role_id, menu_id=payload.menu_id)
    )
