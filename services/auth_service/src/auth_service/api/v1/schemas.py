from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from auth_service.domain.models import UserAuth, IdentityType

class AuthBindResponse(BaseModel):
    id: UUID
    user_id: UUID
    identity_type: IdentityType
    identifier: str
    created_at: datetime

    @classmethod
    def from_domain(cls, auth: UserAuth) -> "AuthBindResponse":
        return cls(
            id=auth.id,
            user_id=auth.user_id,
            identity_type=auth.identity_type,
            identifier=auth.identifier,
            created_at=auth.created_at,
        )
