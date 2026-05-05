from typing import Protocol
from uuid import UUID

class AuthClient(Protocol):
    async def bind_password(
        self,
        *,
        user_id: UUID,
        username: str,
        password: str,
        request_id: str | None = None,
    ) -> None: ...
