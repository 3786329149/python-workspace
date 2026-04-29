from typing import Protocol
from uuid import UUID

from user_service.domain.models import User


class UserCache(Protocol):
    async def get_user(self, user_id: UUID) -> User | None: ...

    async def set_user(self, user: User) -> None: ...

    async def delete_user(self, user_id: UUID) -> None: ...
