from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum, StrEnum
from uuid import UUID, uuid4


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING = "pending"
    DELETED = "deleted"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING = "pending"
    DELETED = "deleted"


class DataScope(IntEnum):
    ALL = 1
    DEPT = 2
    SELF = 3
    CUSTOM = 4



@dataclass(slots=True)
class User:
    id: UUID
    tenant_id: UUID | None
    email: str
    username: str | None
    nickname: str | None
    phone: str | None
    avatar_url: str | None
    status: UserStatus
    is_admin: bool
    dept_id: UUID | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        email: str,
        tenant_id: UUID | None = None,
        username: str | None = None,
        display_name: str | None = None,
        nickname: str | None = None,
        phone: str | None = None,
        avatar_url: str | None = None,
        is_admin: bool = False,
        dept_id: UUID | None = None,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> "User":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            email=normalize_email(email),
            username=normalize_optional(username),
            nickname=normalize_optional(nickname or display_name),
            phone=normalize_optional(phone),
            avatar_url=normalize_optional(avatar_url),
            status=status,
            is_admin=is_admin,
            dept_id=dept_id,
            created_at=now,
            updated_at=now,
        )

    def update_profile(self, changes: dict[str, str | None]) -> None:
        if "display_name" in changes and "nickname" not in changes:
            changes["nickname"] = changes["display_name"]

        for field in ("username", "nickname", "phone", "avatar_url"):
            if field in changes:
                setattr(self, field, normalize_optional(changes[field]))
        self.touch()

    def enable(self) -> None:
        self.status = UserStatus.ACTIVE
        self.deleted_at = None
        self.touch()

    def activate(self) -> None:
        if self.status not in (UserStatus.PENDING, UserStatus.DISABLED):
            raise ValueError(f"cannot activate user from status {self.status}")
        self.status = UserStatus.ACTIVE
        self.deleted_at = None
        self.touch()

    def disable(self) -> None:
        self.status = UserStatus.DISABLED
        self.touch()

    def delete(self) -> None:
        self.status = UserStatus.DELETED
        self.deleted_at = datetime.now(UTC)
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


@dataclass(slots=True)
class Department:
    id: UUID
    tenant_id: UUID
    name: str
    parent_id: UUID | None
    ancestors: str  # comma-separated ancestor IDs, e.g. "id1,id2"
    order_num: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        name: str,
        parent: "Department | None" = None,
        order_num: int = 0,
    ) -> "Department":
        now = datetime.now(UTC)
        if parent is None:
            ancestors = ""
        else:
            parts = [p for p in parent.ancestors.split(",") if p]
            parts.append(str(parent.id))
            ancestors = ",".join(parts)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            parent_id=parent.id if parent else None,
            ancestors=ancestors,
            order_num=order_num,
            created_at=now,
            updated_at=now,
        )

    def rename(self, name: str) -> None:
        self.name = name
        self.updated_at = datetime.now(UTC)

    def ancestor_ids(self) -> list[UUID]:
        """Return list of ancestor UUIDs (root-first)."""
        return [UUID(a) for a in self.ancestors.split(",") if a]

    def build_child_ancestors(self) -> str:
        """Return the ancestors string a direct child of this dept should have."""
        parts = [p for p in self.ancestors.split(",") if p]
        parts.append(str(self.id))
        return ",".join(parts)


@dataclass(slots=True)
class AuditLog:
    id: UUID
    tenant_id: UUID
    user_id: UUID
    action: str
    resource: str
    resource_id: str | None
    details: str | None
    ip_address: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        user_id: UUID,
        action: str,
        resource: str,
        resource_id: str | None = None,
        details: str | None = None,
        ip_address: str | None = None,
        status: str = "success",
    ) -> "AuditLog":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            status=status,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class Role:
    id: UUID
    tenant_id: UUID
    name: str
    role_key: str
    data_scope: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        name: str,
        role_key: str,
        data_scope: int = 1,
    ) -> "Role":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            role_key=role_key,
            data_scope=data_scope,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class Menu:
    id: UUID
    parent_id: UUID | None
    menu_name: str
    menu_type: str
    path: str | None
    perms: str | None
    icon: str | None
    order_num: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        menu_name: str,
        menu_type: str,
        parent_id: UUID | None = None,
        path: str | None = None,
        perms: str | None = None,
        icon: str | None = None,
        order_num: int = 0,
    ) -> "Menu":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            parent_id=parent_id,
            menu_name=menu_name,
            menu_type=menu_type,
            path=path,
            perms=perms,
            icon=icon,
            order_num=order_num,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class Tenant:
    id: UUID
    name: str
    tenant_key: str
    status: TenantStatus
    contact_person: str | None = None
    contact_phone: str | None = None
    config: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    @classmethod
    def create(
        cls,
        name: str,
        tenant_key: str,
        contact_person: str | None = None,
        contact_phone: str | None = None,
        config: dict | None = None,
    ) -> "Tenant":
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            name=name,
            tenant_key=tenant_key,
            status=TenantStatus.ACTIVE,
            contact_person=contact_person,
            contact_phone=contact_phone,
            config=config or {},
            created_at=now,
            updated_at=now,
        )

    def disable(self) -> None:
        self.status = TenantStatus.DISABLED
        self.updated_at = datetime.now(UTC)

    def enable(self) -> None:
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.now(UTC)
