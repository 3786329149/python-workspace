from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from auth_service.domain.models import UserAuth, IdentityType


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterResponse(BaseModel):
    user_id: UUID
    email: str
    username: str
    message: str

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
