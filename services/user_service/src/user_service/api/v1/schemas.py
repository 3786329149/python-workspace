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
    roles: list[str] = []
    permissions: list[str] = []
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    @classmethod
    def from_domain(
        cls, 
        user: User, 
        roles: list[str] | None = None, 
        permissions: list[str] | None = None
    ) -> "UserResponse":
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
            roles=roles or [],
            permissions=permissions or [],
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )


class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    tenant_key: str = Field(..., min_length=2, max_length=50)
    contact_person: str | None = Field(None, max_length=64)
    contact_phone: str | None = Field(None, max_length=32)
    config: dict | None = None
    admin_username: str | None = Field(None, min_length=3, max_length=64)
    admin_email: str | None = None
    admin_password: str = Field("Pass1234", min_length=8)


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    status: str | None = None
    contact_person: str | None = Field(None, max_length=64)
    contact_phone: str | None = Field(None, max_length=32)
    config: dict | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tenant_key: str
    status: str
    contact_person: str | None
    contact_phone: str | None
    config: dict
    created_at: datetime
    updated_at: datetime
