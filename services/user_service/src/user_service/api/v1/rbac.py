"""RBAC API endpoints — permissions query and role/menu management.

All endpoints require X-Internal-Token (supplied by the gateway).
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from user_service.api.deps import get_current_user_id, get_user_service, require_internal_token, require_permission
from user_service.application.commands import (
    AssignMenuToRoleCommand,
    CreateRoleCommand,
    UpdateRoleCommand,
    RemoveMenuFromRoleCommand,
)
from user_service.application.services import UserApplicationService
from user_service.domain.models import Role, Menu

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


class BulkAssignRoleRequest(BaseModel):
    role_ids: list[UUID]


class CreateRoleRequest(BaseModel):
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=50)
    role_key: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z_:]+$")
    data_scope: int = Field(default=1, ge=1, le=4)

class UpdateRoleRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    role_key: str | None = Field(None, min_length=1, max_length=50, pattern=r"^[a-z_:]+$")
    data_scope: int | None = Field(None, ge=1, le=4)


class RoleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    role_key: str
    data_scope: int
    permissions: list[str] = []
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, role: Role, permissions: list[str] | None = None) -> "RoleResponse":
        return cls(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            role_key=role.role_key,
            data_scope=role.data_scope,
            permissions=permissions or [],
            created_at=role.created_at,
            updated_at=role.updated_at,
        )


class UpdateRolePermissionsRequest(BaseModel):
    menu_ids: list[UUID]


class AssignMenuRequest(BaseModel):
    menu_id: UUID

class MenuResponse(BaseModel):
    id: UUID
    parent_id: UUID | None
    menu_name: str
    menu_type: str
    path: str | None
    perms: str | None
    icon: str | None
    order_num: int
    created_at: datetime
    updated_at: datetime


class MenuTreeNode(MenuResponse):
    children: list["MenuTreeNode"] = []


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
    dependencies=[Depends(require_permission("role:assign"))],
)
async def assign_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    """Assign an existing role to a user.

    Automatically invalidates the user's permission cache so the next
    request to ``/me/permissions`` reflects the new role.
    """
    await service.assign_role_to_user(user_id, payload.role_id, actor_id=current_user_id)


@router.put(
    "/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update user roles (bulk replacement)",
    dependencies=[Depends(require_permission("role:assign"))],
)
async def update_user_roles(
    user_id: UUID,
    payload: BulkAssignRoleRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    """Replace all roles for a user with a new set of role IDs."""
    await service.update_user_roles(user_id, payload.role_ids, actor_id=current_user_id)


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a role from a user",
    dependencies=[Depends(require_permission("role:assign"))],
)
async def remove_role(
    user_id: UUID,
    role_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    await service.remove_role_from_user(user_id, role_id, actor_id=current_user_id)


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
    dependencies=[Depends(require_permission("role:create"))],
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
    dependencies=[Depends(require_permission("role:edit"))],
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

@roles_router.delete(
    "/{role_id}/permissions/{menu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a menu/permission-point from a role",
    dependencies=[Depends(require_permission("role:edit"))],
)
async def remove_menu_from_role(
    role_id: UUID,
    menu_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    await service.remove_menu_from_role(
        RemoveMenuFromRoleCommand(role_id=role_id, menu_id=menu_id)
    )

@roles_router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get role details",
    dependencies=[Depends(require_permission("role:list"))],
)
async def get_role(
    role_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> RoleResponse:
    role = await service.get_role(role_id)
    perms = await service.get_role_permissions(role_id)
    return RoleResponse.from_domain(role, perms)

@roles_router.get(
    "",
    response_model=list[RoleResponse],
    summary="List roles",
    dependencies=[Depends(require_permission("role:list"))],
)
async def list_roles(
    tenant_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> list[RoleResponse]:
    roles = await service.get_all_roles(tenant_id)
    results = []
    for r in roles:
        perms = await service.get_role_permissions(r.id)
        results.append(RoleResponse.from_domain(r, perms))
    return results

@roles_router.put(
    "/{role_id}/permissions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update role permissions (bulk)",
    dependencies=[Depends(require_permission("role:edit"))],
)
async def update_role_permissions(
    role_id: UUID,
    payload: UpdateRolePermissionsRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    """Replace all permissions for a role with a new set of menu IDs."""
    await service.update_role_permissions(role_id, payload.menu_ids, actor_id=current_user_id)

@roles_router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
    dependencies=[Depends(require_permission("role:edit"))],
)
async def update_role(
    role_id: UUID,
    payload: UpdateRoleRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> RoleResponse:
    role = await service.update_role(
        UpdateRoleCommand(
            role_id=role_id,
            **payload.model_dump(exclude_unset=True)
        )
    )
    return RoleResponse.from_domain(role)

@roles_router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
    dependencies=[Depends(require_permission("role:delete"))],
)
async def delete_role(
    role_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    await service.delete_role(role_id)

menus_router = APIRouter(
    prefix="/menus",
    tags=["rbac"],
    dependencies=[Depends(require_internal_token), Depends(require_permission("role:list"))],
)

@menus_router.get(
    "",
    response_model=list[MenuResponse],
    summary="List all available menus and permissions",
)
async def list_menus(
    service: UserApplicationService = Depends(get_user_service),
) -> list[MenuResponse]:
    menus = await service.get_all_menus()
    return [
        MenuResponse(
            id=m.id,
            parent_id=m.parent_id,
            menu_name=m.menu_name,
            menu_type=m.menu_type,
            path=m.path,
            perms=m.perms,
            icon=m.icon,
            order_num=m.order_num,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in menus
    ]


@menus_router.get(
    "/tree",
    response_model=list[MenuTreeNode],
    summary="Get menu tree structure",
)
async def get_menu_tree(
    service: UserApplicationService = Depends(get_user_service),
) -> list[MenuTreeNode]:
    """Return nested menu tree for sidebar rendering."""
    tree = await service.get_menu_tree()
    return tree  # type: ignore
