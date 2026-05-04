from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

@dataclass
class RefreshTokenSession:
    user_id: UUID
    expires_at: int
    revoked_at: int | None = None
    replaced_by: str | None = None

class RefreshTokenStore(Protocol):
    async def save(self, jti: str, session: RefreshTokenSession) -> None: ...
    async def get(self, jti: str) -> RefreshTokenSession | None: ...
    async def revoke(self, jti: str) -> None: ...
    async def revoke_all_for_user(self, user_id: UUID) -> None: ...
