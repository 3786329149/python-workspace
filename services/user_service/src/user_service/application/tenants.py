from uuid import UUID
from datetime import datetime, UTC
from user_service.application.commands import CreateTenantCommand, UpdateTenantCommand
from user_service.application.unit_of_work import UserUnitOfWork
from user_service.application.auth_client import AuthClient
from user_service.domain.models import Tenant, Department, Role, TenantStatus, User
from common.errors import AppError

class TenantApplicationService:
    def __init__(self, uow: UserUnitOfWork, auth_client: AuthClient | None = None) -> None:
        self.uow = uow
        self.auth_client = auth_client

    async def create_tenant(self, command: CreateTenantCommand, *, request_id: str | None = None) -> Tenant:
        async with self.uow:
            # Check for existing key
            existing = await self.uow.tenants.get_by_key(command.tenant_key)
            if existing:
                raise AppError(f"tenant_key '{command.tenant_key}' already exists", code="TENANT_ALREADY_EXISTS", status_code=409)

            tenant = Tenant.create(
                name=command.name,
                tenant_key=command.tenant_key,
                contact_person=command.contact_person,
                contact_phone=command.contact_phone,
                config=command.config,
            )
            await self.uow.tenants.add(tenant)

            # Auto-initialize tenant data
            # 1. Root department
            root_dept = Department.create(
                tenant_id=tenant.id,
                name=f"{tenant.name}总部",
            )
            await self.uow.departments.add(root_dept)

            # 2. Default roles
            admin_role = Role.create(
                tenant_id=tenant.id,
                name="管理员",
                role_key="admin",
                data_scope=1, # ALL
            )
            user_role = Role.create(
                tenant_id=tenant.id,
                name="普通员工",
                role_key="user",
                data_scope=3, # SELF
            )
            await self.uow.roles.add(admin_role)
            await self.uow.roles.add(user_role)

            # 3. Create Root Admin User
            admin_username = command.admin_username or f"admin_{command.tenant_key}"
            admin_email = command.admin_email or f"admin@{command.tenant_key}.com"
            
            # Check if user already exists (globally by email/username in user_service)
            # This is a bit tricky as users might exist in other tenants, but email should be globally unique in this design?
            # UserRecord has email unique=True.
            existing_user = await self.uow.users.get_by_email(admin_email)
            if existing_user:
                 raise AppError(f"admin email '{admin_email}' already exists", code="ADMIN_USER_EXISTS", status_code=409)

            admin_user = User.create(
                email=admin_email,
                tenant_id=tenant.id,
                username=admin_username,
                nickname="Administrator",
                is_admin=True,
                dept_id=root_dept.id,
            )
            await self.uow.users.add(admin_user)
            # Flush to DB so FK constraints are satisfied for role assignment
            await self.uow.flush() 
            await self.uow.roles.assign_role_to_user(admin_user.id, admin_role.id)

            # 4. Bind Password in Auth Service
            if self.auth_client:
                await self.auth_client.bind_password(
                    user_id=admin_user.id,
                    username=admin_username,
                    password=command.admin_password,
                    request_id=request_id,
                )

            await self.uow.commit()
            return tenant

    async def get_tenant(self, tenant_id: UUID) -> Tenant:
        async with self.uow:
            tenant = await self.uow.tenants.get_by_id(tenant_id)
            if not tenant:
                raise AppError("tenant not found", code="TENANT_NOT_FOUND", status_code=404)
            return tenant

    async def list_tenants(self) -> list[Tenant]:
        async with self.uow:
            return await self.uow.tenants.get_all()

    async def update_tenant(self, command: UpdateTenantCommand) -> Tenant:
        async with self.uow:
            tenant = await self.uow.tenants.get_by_id(command.tenant_id)
            if not tenant:
                raise AppError("tenant not found", code="TENANT_NOT_FOUND", status_code=404)
            
            if command.name is not None:
                tenant.name = command.name
            if command.status is not None:
                tenant.status = TenantStatus(command.status)
            if command.contact_person is not None:
                tenant.contact_person = command.contact_person
            if command.contact_phone is not None:
                tenant.contact_phone = command.contact_phone
            if command.config is not None:
                tenant.config.update(command.config)
            
            tenant.updated_at = datetime.now(UTC)
            
            await self.uow.tenants.save(tenant)
            await self.uow.commit()
            return tenant

    async def delete_tenant(self, tenant_id: UUID) -> None:
        async with self.uow:
            tenant = await self.uow.tenants.get_by_id(tenant_id)
            if not tenant:
                raise AppError("tenant not found", code="TENANT_NOT_FOUND", status_code=404)
            await self.uow.tenants.delete(tenant_id)
            await self.uow.commit()
