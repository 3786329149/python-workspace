"""Tests for Phase 5 RBAC: permissions endpoint and gateway permission checker."""
import asyncio
import json
from datetime import UTC, datetime
from typing import Self
from types import TracebackType
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from user_service.application.services import UserApplicationService
from user_service.domain.models import Menu, Role, User, UserStatus
from user_service.domain.errors import UserNotFound


# ---------------------------------------------------------------------------
# In-memory stubs for UserApplicationService
# ---------------------------------------------------------------------------

class InMemoryUserRepo:
    def __init__(self):
        self._store: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self._store[user.id] = user

    async def save(self, user: User) -> None:
        self._store[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._store.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._store.values() if u.email == email), None)

    async def get_by_username(self, username: str) -> User | None:
        return next((u for u in self._store.values() if u.username == username), None)

    async def get_by_phone(self, phone: str) -> User | None:
        return next((u for u in self._store.values() if u.phone == phone), None)


class InMemoryRoleRepo:
    def __init__(self):
        self._roles: dict[UUID, Role] = {}
        self._user_roles: list[tuple[UUID, UUID]] = []  # (user_id, role_id)

    async def add(self, role: Role) -> None:
        self._roles[role.id] = role

    async def save(self, role: Role) -> None:
        self._roles[role.id] = role

    async def get_by_id(self, role_id: UUID) -> Role | None:
        return self._roles.get(role_id)

    async def get_by_user_id(self, user_id: UUID) -> list[Role]:
        role_ids = {rid for uid, rid in self._user_roles if uid == user_id}
        return [r for rid, r in self._roles.items() if rid in role_ids]

    async def get_by_tenant_id(self, tenant_id: UUID) -> list[Role]:
        return [r for r in self._roles.values() if r.tenant_id == tenant_id]

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        if (user_id, role_id) not in self._user_roles:
            self._user_roles.append((user_id, role_id))


class InMemoryMenuRepo:
    def __init__(self):
        self._menus: dict[UUID, Menu] = {}
        self._role_menus: list[tuple[UUID, UUID]] = []  # (role_id, menu_id)

    async def add(self, menu: Menu) -> None:
        self._menus[menu.id] = menu

    async def get_by_role_id(self, role_id: UUID) -> list[Menu]:
        menu_ids = {mid for rid, mid in self._role_menus if rid == role_id}
        return [m for mid, m in self._menus.items() if mid in menu_ids]

    async def get_by_user_id(self, user_id: UUID) -> list[Menu]:
        # stub: return all menus (simplified)
        return list(self._menus.values())

    async def assign_menu_to_role(self, role_id: UUID, menu_id: UUID) -> None:
        if (role_id, menu_id) not in self._role_menus:
            self._role_menus.append((role_id, menu_id))


class InMemoryUoW:
    def __init__(self):
        self.users = InMemoryUserRepo()
        self.roles = InMemoryRoleRepo()
        self.menus = InMemoryMenuRepo()
        self._committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests: get_user_permissions
# ---------------------------------------------------------------------------

def test_get_user_permissions_returns_f_type_perms_only() -> None:
    """Only menus with type='F' and non-null perms should be returned."""

    async def run() -> None:
        uow = InMemoryUoW()
        now = datetime.now(UTC)
        tenant_id = uuid4()
        user_id = uuid4()

        # Add menus: one is a button (F), one is a menu (C)
        btn_menu = Menu(
            id=uuid4(), parent_id=None, menu_name="User List Button",
            menu_type="F", path=None, perms="user:list",
            icon=None, order_num=0, created_at=now, updated_at=now,
        )
        dir_menu = Menu(
            id=uuid4(), parent_id=None, menu_name="User Dir",
            menu_type="C", path="/users", perms="user:dir",
            icon=None, order_num=0, created_at=now, updated_at=now,
        )
        await uow.menus.add(btn_menu)
        await uow.menus.add(dir_menu)

        service = UserApplicationService(uow)
        perms = await service.get_user_permissions(user_id)

        assert "user:list" in perms
        assert "user:dir" not in perms

    asyncio.run(run())


def test_get_user_permissions_uses_cache() -> None:
    """When cache returns data, DB is not queried."""

    class HitCache:
        async def get_permissions(self, user_id: UUID) -> list[str] | None:
            return ["cached:perm"]

        async def set_permissions(self, uid, perms, *, ttl=300):
            pass

        async def delete_permissions(self, uid):
            pass

        async def get_user(self, uid): return None
        async def set_user(self, u): pass
        async def delete_user(self, uid): pass

    async def run() -> None:
        uow = InMemoryUoW()
        service = UserApplicationService(uow, cache=HitCache())
        perms = await service.get_user_permissions(uuid4())
        assert perms == ["cached:perm"]

    asyncio.run(run())


def test_assign_role_to_user_raises_on_unknown_user() -> None:
    async def run() -> None:
        uow = InMemoryUoW()
        service = UserApplicationService(uow)
        with pytest.raises(UserNotFound):
            await service.assign_role_to_user(uuid4(), uuid4())

    asyncio.run(run())


def test_assign_role_to_user_invalidates_cache() -> None:
    """After assigning a role the permission cache key must be deleted."""

    deleted_ids: list[UUID] = []

    class TrackingCache:
        async def get_permissions(self, uid): return None
        async def set_permissions(self, uid, perms, *, ttl=300): pass
        async def delete_permissions(self, uid):
            deleted_ids.append(uid)
        async def get_user(self, uid): return None
        async def set_user(self, u): pass
        async def delete_user(self, uid): pass

    async def run() -> None:
        now = datetime.now(UTC)
        uow = InMemoryUoW()
        user_id = uuid4()
        tenant_id = uuid4()
        role_id = uuid4()

        user = User(
            id=user_id, tenant_id=None, email="u@test.com",
            username=None, nickname=None, phone=None, avatar_url=None,
            status=UserStatus.ACTIVE, is_admin=False, dept_id=None,
            created_at=now, updated_at=now,
        )
        role = Role(
            id=role_id, tenant_id=tenant_id, name="Editor",
            role_key="editor", data_scope=1,
            created_at=now, updated_at=now,
        )
        await uow.users.add(user)
        await uow.roles.add(role)

        service = UserApplicationService(uow, cache=TrackingCache())
        await service.assign_role_to_user(user_id, role_id)

        assert user_id in deleted_ids

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Tests: gateway PermissionChecker
# ---------------------------------------------------------------------------

def test_permission_checker_key_format() -> None:
    from gateway.core.permissions import _perm_key
    uid = "abc-123"
    assert _perm_key(uid) == f"permission:user:{uid}"
