from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.domain.models import User, UserStatus, normalize_email
from user_service.infrastructure.db.models import UserRecord


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
