from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from auth_service.domain.models import UserAuth, IdentityType
from auth_service.domain.repositories import AuthRepository
from .models import UserAuthRecord

class SqlAlchemyAuthRepository(AuthRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, auth: UserAuth) -> None:
        record = UserAuthRecord(
            id=auth.id,
            user_id=auth.user_id,
            identity_type=auth.identity_type.value,
            identifier=auth.identifier,
            credential=auth.credential,
            created_at=auth.created_at,
            updated_at=auth.updated_at,
        )
        self.session.add(record)

    async def get_by_identifier(self, identity_type: IdentityType, identifier: str) -> UserAuth | None:
        stmt = select(UserAuthRecord).where(
            UserAuthRecord.identity_type == identity_type.value,
            UserAuthRecord.identifier == identifier,
            UserAuthRecord.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_domain(record) if record else None

    async def get_by_user_id(self, user_id: UUID, identity_type: IdentityType) -> UserAuth | None:
        stmt = select(UserAuthRecord).where(
            UserAuthRecord.user_id == user_id,
            UserAuthRecord.identity_type == identity_type.value,
            UserAuthRecord.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_domain(record) if record else None

    async def save(self, auth: UserAuth) -> None:
        stmt = select(UserAuthRecord).where(UserAuthRecord.id == auth.id)
        result = await self.session.execute(stmt)
        record = result.scalar_one()
        
        record.identifier = auth.identifier
        record.credential = auth.credential
        record.updated_at = auth.updated_at
        record.deleted_at = auth.deleted_at

    def _to_domain(self, record: UserAuthRecord) -> UserAuth:
        return UserAuth(
            id=record.id,
            user_id=record.user_id,
            identity_type=IdentityType(record.identity_type),
            identifier=record.identifier,
            credential=record.credential,
            created_at=record.created_at,
            updated_at=record.updated_at,
            deleted_at=record.deleted_at,
        )
