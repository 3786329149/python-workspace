"""RBAC endpoints — permissions and role assignment.

All endpoints require X-Internal-Token (gateway enforces this).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status

from user_service.api.deps import get_current_user_id, get_user_service, require_internal_token
from user_service.application.services import UserApplicationService
from pydantic import BaseModel

router = APIRouter(
    prefix="/users",
    tags=["rbac"],
    dependencies=[Depends(require_internal_token)],
)


class PermissionsResponse(BaseModel):
    user_id: UUID
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    role_id: UUID


@router.get(
    "/me/permissions",
    response_model=PermissionsResponse,
)
async def get_my_permissions(
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> PermissionsResponse:
    """Return the permission keys (e.g. user:list) for the calling user.

    Results are cached in Redis for 5 minutes (key: permission:user:{user_id}).
    """
    perms = await service.get_user_permissions(current_user_id)
    return PermissionsResponse(user_id=current_user_id, permissions=perms)


@router.post(
    "/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> None:
    """Assign a role to a user.  Invalidates the user's permission cache."""
    await service.assign_role_to_user(user_id, payload.role_id)
