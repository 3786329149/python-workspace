from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from user_service.domain.models import User, UserStatus


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    tenant_id: UUID | None = None
    username: str | None = Field(default=None, min_length=3, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = None
    is_admin: bool = False
    dept_id: UUID | None = None


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=3, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)
    nickname: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = None


class UserAdminUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=64)
    nickname: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = None
    status: UserStatus | None = None
    is_admin: bool | None = None
    dept_id: UUID | None = None


class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None
    email: str
    username: str | None
    display_name: str | None
    nickname: str | None
    phone: str | None
    avatar_url: str | None
    status: UserStatus
    is_admin: bool
    dept_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            username=user.username,
            display_name=user.nickname,
            nickname=user.nickname,
            phone=user.phone,
            avatar_url=user.avatar_url,
            status=user.status,
            is_admin=user.is_admin,
            dept_id=user.dept_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )
