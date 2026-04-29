from types import TracebackType
from typing import Self
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from auth_service.application.unit_of_work import AuthUnitOfWork
from .repositories import SqlAlchemyAuthRepository

class SqlAlchemyAuthUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.session: AsyncSession | None = None
        self.auths: SqlAlchemyAuthRepository

    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        self.auths = SqlAlchemyAuthRepository(self.session)
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
