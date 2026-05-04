
with open('services/user_service/src/user_service/infrastructure/db/repositories.py', 'a', encoding='utf-8') as f:
    f.write('''
from sqlalchemy import join
from user_service.domain.models import Role, Menu
from user_service.infrastructure.db.models import RoleRecord, MenuRecord, user_roles, role_menus

class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> list[Role]:
        stmt = select(RoleRecord).join(user_roles, user_roles.c.role_id == RoleRecord.id).where(user_roles.c.user_id == user_id, RoleRecord.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [Role(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            role_key=r.role_key,
            data_scope=r.data_scope,
            created_at=r.created_at,
            updated_at=r.updated_at,
            deleted_at=r.deleted_at,
        ) for r in records]

class SqlAlchemyMenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> list[Menu]:
        stmt = select(MenuRecord).join(role_menus, role_menus.c.menu_id == MenuRecord.id).join(user_roles, user_roles.c.role_id == role_menus.c.role_id).where(user_roles.c.user_id == user_id, MenuRecord.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        return [Menu(
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
        ) for r in records]
''')

