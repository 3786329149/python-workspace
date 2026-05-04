"""Department management API endpoints.

All endpoints require X-Internal-Token (supplied by the gateway).
The tree endpoint is also available for authenticated end-users via the gateway.
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from user_service.api.deps import get_current_user_id, get_user_service, require_internal_token, require_permission
from user_service.application.commands import CreateDepartmentCommand, UpdateDepartmentCommand
from user_service.application.services import UserApplicationService

router = APIRouter(
    prefix="/depts",
    tags=["departments"],
    dependencies=[Depends(require_internal_token)],
)

# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #

class DeptCreateRequest(BaseModel):
    tenant_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: UUID | None = None
    order_num: int = Field(default=0, ge=0)


class DeptUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    order_num: int | None = Field(default=None, ge=0)


class DeptResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    parent_id: UUID | None
    ancestors: str
    order_num: int
    created_at: datetime
    updated_at: datetime


class DeptTreeNode(BaseModel):
    id: str
    tenant_id: str
    name: str
    parent_id: str | None
    ancestors: str
    order_num: int
    created_at: str
    updated_at: str
    children: list["DeptTreeNode"] = []


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get(
    "/tree",
    response_model=list[DeptTreeNode],
    summary="Get full department tree for a tenant",
    dependencies=[Depends(require_permission("dept:list"))],
)
async def get_dept_tree(
    tenant_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    service: UserApplicationService = Depends(get_user_service),
) -> list[DeptTreeNode]:
    """Return the nested department tree for *tenant_id*.

    Root nodes (no parent) appear at the top level;
    each node carries a ``children`` list.
    """
    tree = await service.get_department_tree(tenant_id, current_user_id=current_user_id)
    # Pydantic will recursively validate via DeptTreeNode
    return tree  # type: ignore[return-value]


@router.get(
    "/{dept_id}",
    response_model=DeptResponse,
    summary="Get a single department",
    dependencies=[Depends(require_permission("dept:list"))],
)
async def get_department(
    dept_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> DeptResponse:
    dept = await service.get_department(dept_id)
    return DeptResponse(
        id=dept.id,
        tenant_id=dept.tenant_id,
        name=dept.name,
        parent_id=dept.parent_id,
        ancestors=dept.ancestors,
        order_num=dept.order_num,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.post(
    "",
    response_model=DeptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
    dependencies=[Depends(require_permission("dept:create"))],
)
async def create_department(
    payload: DeptCreateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> DeptResponse:
    """Create a department.

    - If *parent_id* is ``null`` the department becomes a root node.
    - ``ancestors`` is computed automatically from the parent chain.
    - Returns 404 if *parent_id* does not exist.
    """
    dept = await service.create_department(
        CreateDepartmentCommand(
            tenant_id=payload.tenant_id,
            name=payload.name,
            parent_id=payload.parent_id,
            order_num=payload.order_num,
        )
    )
    return DeptResponse(
        id=dept.id,
        tenant_id=dept.tenant_id,
        name=dept.name,
        parent_id=dept.parent_id,
        ancestors=dept.ancestors,
        order_num=dept.order_num,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.patch(
    "/{dept_id}",
    response_model=DeptResponse,
    summary="Rename or reorder a department",
    dependencies=[Depends(require_permission("dept:edit"))],
)
async def update_department(
    dept_id: UUID,
    payload: DeptUpdateRequest,
    service: UserApplicationService = Depends(get_user_service),
) -> DeptResponse:
    dept = await service.update_department(
        UpdateDepartmentCommand(
            dept_id=dept_id,
            name=payload.name,
            order_num=payload.order_num,
        )
    )
    return DeptResponse(
        id=dept.id,
        tenant_id=dept.tenant_id,
        name=dept.name,
        parent_id=dept.parent_id,
        ancestors=dept.ancestors,
        order_num=dept.order_num,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.delete(
    "/{dept_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department (soft-delete)",
    dependencies=[Depends(require_permission("dept:delete"))],
)
async def delete_department(
    dept_id: UUID,
    service: UserApplicationService = Depends(get_user_service),
) -> Response:
    """Soft-delete a department.

    Returns 409 if the department still has active sub-departments.
    """
    await service.delete_department(dept_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
