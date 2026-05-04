from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.domain.models import Department, Menu, Role, User, UserStatus, normalize_email
from user_service.infrastructure.db.models import (
    DepartmentRecord,
    MenuRecord,
    RoleRecord,
    UserRecord,
    role_menus,
    user_roles,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user: User) -> None:
        self.session.add(UserRecord.from_domain(user))

    async def save(self, user: User) -> None:
        record = await self.session.get(UserRecord, user.id)
        if record is None:
            await self.add(user)
            return

        record.apply(user)

    async def get_by_id(self, user_id: UUID) -> User | None:
        record = await self.session.get(UserRecord, user_id)
        if record is None or record.status == UserStatus.DELETED.value:
            return None
        return record.to_domain()

    async def get_by_email(self, email: str) -> User | None:
        return await self._get_one_by(UserRecord.email == normalize_email(email))

    async def get_by_username(self, username: str) -> User | None:
        return await self._get_one_by(UserRecord.username == username)

    async def get_by_phone(self, phone: str) -> User | None:
        return await self._get_one_by(UserRecord.phone == phone)

    async def _get_one_by(self, criterion) -> User | None:
        result = await self.session.execute(
            select(UserRecord).where(
                criterion,
                UserRecord.status != UserStatus.DELETED.value,
            )
        )
        record = result.scalar_one_or_none()
        return record.to_domain() if record else None

    async def get_all(self, tenant_id: UUID | None = None) -> list[User]:
        stmt = select(UserRecord).where(UserRecord.status != UserStatus.DELETED.value)
        if tenant_id:
            stmt = stmt.where(UserRecord.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return [r.to_domain() for r in result.scalars().all()]

    async def delete(self, user_id: UUID) -> None:
        from datetime import UTC, datetime
        record = await self.session.get(UserRecord, user_id)
        if record is not None:
            record.status = UserStatus.DELETED.value
            record.deleted_at = datetime.now(UTC)


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, role: Role) -> None:
        record = RoleRecord(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            role_key=role.role_key,
            data_scope=role.data_scope,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
        self.session.add(record)

    async def get_by_id(self, role_id: UUID) -> Role | None:
        record = await self.session.get(RoleRecord, role_id)
        if record is None or record.deleted_at is not None:
            return None
        return self._to_domain(record)

    async def get_by_user_id(self, user_id: UUID) -> list[Role]:
        stmt = (
            select(RoleRecord)
            .join(user_roles, user_roles.c.role_id == RoleRecord.id)
            .where(user_roles.c.user_id == user_id, RoleRecord.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_by_tenant_id(self, tenant_id: UUID) -> list[Role]:
        stmt = select(RoleRecord).where(
            RoleRecord.tenant_id == tenant_id, RoleRecord.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(user_roles).values(user_id=user_id, role_id=role_id).on_conflict_do_nothing()
        await self.session.execute(stmt)

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        from sqlalchemy import delete
        stmt = delete(user_roles).where(user_roles.c.user_id == user_id, user_roles.c.role_id == role_id)
        await self.session.execute(stmt)

    async def delete(self, role_id: UUID) -> None:
        from datetime import UTC, datetime
        record = await self.session.get(RoleRecord, role_id)
        if record is not None:
            record.deleted_at = datetime.now(UTC)

    def _to_domain(self, r: RoleRecord) -> Role:
        return Role(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            role_key=r.role_key,
            data_scope=r.data_scope,
            created_at=r.created_at,
            updated_at=r.updated_at,
            deleted_at=r.deleted_at,
        )


class SqlAlchemyMenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_role_id(self, role_id: UUID) -> list[Menu]:
        stmt = (
            select(MenuRecord)
            .join(role_menus, role_menus.c.menu_id == MenuRecord.id)
            .where(role_menus.c.role_id == role_id, MenuRecord.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_by_user_id(self, user_id: UUID) -> list[Menu]:
        stmt = (
            select(MenuRecord)
            .join(role_menus, role_menus.c.menu_id == MenuRecord.id)
            .join(user_roles, user_roles.c.role_id == role_menus.c.role_id)
            .where(user_roles.c.user_id == user_id, MenuRecord.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_all(self) -> list[Menu]:
        stmt = select(MenuRecord).where(MenuRecord.deleted_at.is_(None)).order_by(MenuRecord.order_num)
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def assign_menu_to_role(self, role_id: UUID, menu_id: UUID) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(role_menus).values(role_id=role_id, menu_id=menu_id).on_conflict_do_nothing()
        await self.session.execute(stmt)

    async def remove_menu_from_role(self, role_id: UUID, menu_id: UUID) -> None:
        from sqlalchemy import delete
        stmt = delete(role_menus).where(role_menus.c.role_id == role_id, role_menus.c.menu_id == menu_id)
        await self.session.execute(stmt)

    def _to_domain(self, r: MenuRecord) -> Menu:
        return Menu(
            id=r.id,
            parent_id=r.parent_id,
            menu_name=r.menu_name,
            menu_type=r.menu_type,
            path=r.path,
            perms=r.perms,
            icon=r.icon,
            order_num=r.order_num,
            created_at=r.created_at,
            updated_at=r.updated_at,
            deleted_at=r.deleted_at,
        )


class SqlAlchemyDepartmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, dept: Department) -> None:
        self.session.add(self._to_record(dept))

    async def save(self, dept: Department) -> None:
        record = await self.session.get(DepartmentRecord, dept.id)
        if record is None:
            await self.add(dept)
            return
        record.name = dept.name
        record.parent_id = dept.parent_id
        record.ancestors = dept.ancestors
        record.order_num = dept.order_num
        record.updated_at = dept.updated_at
        record.deleted_at = dept.deleted_at

    async def get_by_id(self, dept_id: UUID) -> Department | None:
        record = await self.session.get(DepartmentRecord, dept_id)
        if record is None or record.deleted_at is not None:
            return None
        return self._to_domain(record)

    async def get_by_tenant_id(self, tenant_id: UUID) -> list[Department]:
        stmt = select(DepartmentRecord).where(
            DepartmentRecord.tenant_id == tenant_id,
            DepartmentRecord.deleted_at.is_(None),
        ).order_by(DepartmentRecord.order_num)
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_children(self, parent_id: UUID) -> list[Department]:
        stmt = select(DepartmentRecord).where(
            DepartmentRecord.parent_id == parent_id,
            DepartmentRecord.deleted_at.is_(None),
        ).order_by(DepartmentRecord.order_num)
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_descendants(self, dept_id: UUID) -> list[Department]:
        """Return all departments that have dept_id anywhere in their ancestors path."""
        from sqlalchemy import cast, String
        stmt = select(DepartmentRecord).where(
            DepartmentRecord.ancestors.contains(str(dept_id)),
            DepartmentRecord.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def delete(self, dept_id: UUID) -> None:
        """Soft-delete a department (set deleted_at)."""
        from datetime import UTC, datetime
        record = await self.session.get(DepartmentRecord, dept_id)
        if record is not None:
            record.deleted_at = datetime.now(UTC)

    def _to_record(self, dept: Department) -> DepartmentRecord:
        record = DepartmentRecord(id=dept.id)
        record.tenant_id = dept.tenant_id
        record.name = dept.name
        record.parent_id = dept.parent_id
        record.ancestors = dept.ancestors
        record.order_num = dept.order_num
        record.created_at = dept.created_at
        record.updated_at = dept.updated_at
        record.deleted_at = dept.deleted_at
        return record

    def _to_domain(self, r: DepartmentRecord) -> Department:
        return Department(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            parent_id=r.parent_id,
            ancestors=r.ancestors or "",
            order_num=r.order_num,
            created_at=r.created_at,
            updated_at=r.updated_at,
            deleted_at=r.deleted_at,
        )

