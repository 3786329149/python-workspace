from uuid import UUID
from fastapi import APIRouter, Depends, Response, status

from user_service.api.deps import get_tenant_service, require_platform_admin
from user_service.api.v1.schemas import TenantCreateRequest, TenantResponse, TenantUpdateRequest
from user_service.application.commands import CreateTenantCommand, UpdateTenantCommand
from user_service.application.tenants import TenantApplicationService

router = APIRouter(prefix="/tenants", tags=["tenants"])

@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_platform_admin)],
)
async def create_tenant(
    payload: TenantCreateRequest,
    service: TenantApplicationService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = await service.create_tenant(CreateTenantCommand(**payload.model_dump()))
    return TenantResponse.model_validate(tenant)

@router.get(
    "",
    response_model=list[TenantResponse],
    dependencies=[Depends(require_platform_admin)],
)
async def list_tenants(
    service: TenantApplicationService = Depends(get_tenant_service),
) -> list[TenantResponse]:
    tenants = await service.list_tenants()
    return [TenantResponse.model_validate(t) for t in tenants]

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_platform_admin)],
)
async def get_tenant(
    tenant_id: UUID,
    service: TenantApplicationService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = await service.get_tenant(tenant_id)
    return TenantResponse.model_validate(tenant)

@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    dependencies=[Depends(require_platform_admin)],
)
async def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdateRequest,
    service: TenantApplicationService = Depends(get_tenant_service),
) -> TenantResponse:
    tenant = await service.update_tenant(
        UpdateTenantCommand(tenant_id=tenant_id, **payload.model_dump(exclude_unset=True))
    )
    return TenantResponse.model_validate(tenant)

@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_platform_admin)],
)
async def delete_tenant(
    tenant_id: UUID,
    service: TenantApplicationService = Depends(get_tenant_service),
) -> Response:
    await service.delete_tenant(tenant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
