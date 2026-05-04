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


@dataclass(frozen=True, slots=True)
class CreateRoleCommand:
    tenant_id: UUID
    name: str
    role_key: str
    data_scope: int = 1


@dataclass(frozen=True, slots=True)
class AssignMenuToRoleCommand:
    role_id: UUID
    menu_id: UUID


@dataclass(frozen=True, slots=True)
class CreateDepartmentCommand:
    tenant_id: UUID
    name: str
    parent_id: UUID | None = None
    order_num: int = 0


@dataclass(frozen=True, slots=True)
class UpdateDepartmentCommand:
    dept_id: UUID
    name: str | None = None
    order_num: int | None = None


@dataclass(frozen=True, slots=True)
class UpdateRoleCommand:
    role_id: UUID
    name: str | None = None
    role_key: str | None = None
    data_scope: int | None = None


@dataclass(frozen=True, slots=True)
class RemoveMenuFromRoleCommand:
    role_id: UUID
    menu_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateUserAdminCommand:
    user_id: UUID
    email: str | None = None
    username: str | None = None
    nickname: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    status: str | None = None
    is_admin: bool | None = None
    dept_id: UUID | None = None
