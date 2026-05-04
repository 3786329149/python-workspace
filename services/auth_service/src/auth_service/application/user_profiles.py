from typing import Protocol
from uuid import UUID


class UserProfileClient(Protocol):
    async def create_user(
        self,
        *,
        email: str,
        username: str,
        request_id: str | None = None,
    ) -> dict[str, object]: ...

    async def delete_user(
        self,
        user_id: UUID,
        *,
        request_id: str | None = None,
    ) -> None: ...

    async def activate_user(
        self,
        user_id: UUID,
        *,
        request_id: str | None = None,
    ) -> dict[str, object]: ...
