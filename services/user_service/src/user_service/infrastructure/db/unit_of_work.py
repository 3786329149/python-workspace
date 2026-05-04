from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from user_service.infrastructure.db.repositories import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyMenuRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.session: AsyncSession | None = None
        self.users: SqlAlchemyUserRepository
        self.roles: SqlAlchemyRoleRepository
        self.menus: SqlAlchemyMenuRepository
        self.departments: SqlAlchemyDepartmentRepository

    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        self.roles = SqlAlchemyRoleRepository(self.session)
        self.menus = SqlAlchemyMenuRepository(self.session)
        self.departments = SqlAlchemyDepartmentRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.session is None:
            return

        if exc_type is not None:
            await self.rollback()

        await self.session.close()

    async def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work has not been entered")
        await self.session.commit()

    async def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("unit of work has not been entered")
        await self.session.rollback()
