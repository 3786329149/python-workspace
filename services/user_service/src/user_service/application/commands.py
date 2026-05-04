from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    tenant_id: UUID | None = None
    username: str | None = None
    display_name: str | None = None
    nickname: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    is_admin: bool = False
    dept_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateUserProfileCommand:
    user_id: UUID
    changes: dict[str, str | None]


@dataclass(frozen=True, slots=True)
class UserIdCommand:
    user_id: UUID


@dataclass(frozen=True, slots=True)
class CreateRegistrationProfileCommand:
    email: str
    username: str | None = None
