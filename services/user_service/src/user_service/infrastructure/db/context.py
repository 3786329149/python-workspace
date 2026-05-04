from contextvars import ContextVar
from uuid import UUID

tenant_id_var: ContextVar[UUID | None] = ContextVar("tenant_id", default=None)


def set_current_tenant(tenant_id: UUID | None) -> None:
    tenant_id_var.set(tenant_id)


def get_current_tenant() -> UUID | None:
    return tenant_id_var.get()
