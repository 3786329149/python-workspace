from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

class IdentityType(str, Enum):
    PASSWORD = "password"
    WECHAT = "wechat"
    MOBILE = "mobile"

@dataclass
class UserAuth:
    id: UUID
    user_id: UUID
    identity_type: IdentityType
    identifier: str
    credential: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def create_password_auth(cls, user_id: UUID, username: str, hashed_password: str) -> "UserAuth":
        now = datetime.now()
        return cls(
            id=uuid4(),
            user_id=user_id,
            identity_type=IdentityType.PASSWORD,
            identifier=username,
            credential=hashed_password,
            created_at=now,
            updated_at=now,
        )
