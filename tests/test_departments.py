"""Tests for Department domain model and ApplicationService."""
import asyncio
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

import pytest

from user_service.application.commands import CreateDepartmentCommand, UpdateDepartmentCommand
from user_service.application.services import UserApplicationService, _build_tree
from user_service.domain.models import Department, User, UserStatus


# ---------------------------------------------------------------------------
# In-memory stubs
# ---------------------------------------------------------------------------

class InMemoryDeptRepo:
    def __init__(self):
        self._store: dict[UUID, Department] = {}

    async def add(self, dept: Department) -> None:
        self._store[dept.id] = dept

    async def save(self, dept: Department) -> None:
        self._store[dept.id] = dept

    async def get_by_id(self, dept_id: UUID) -> Department | None:
        d = self._store.get(dept_id)
        return d if (d and d.deleted_at is None) else None

    async def get_by_tenant_id(self, tenant_id: UUID) -> list[Department]:
        return [d for d in self._store.values() if d.tenant_id == tenant_id and d.deleted_at is None]

    async def get_children(self, parent_id: UUID) -> list[Department]:
        return [d for d in self._store.values() if d.parent_id == parent_id and d.deleted_at is None]

    async def get_descendants(self, dept_id: UUID) -> list[Department]:
        return [d for d in self._store.values() if str(dept_id) in d.ancestors and d.deleted_at is None]

    async def delete(self, dept_id: UUID) -> None:
        if dept_id in self._store:
            self._store[dept_id].deleted_at = datetime.now(UTC)


class InMemoryUserRepo:
    async def add(self, u): pass
    async def save(self, u): pass
    async def get_by_id(self, uid): return None
    async def get_by_email(self, e): return None
    async def get_by_username(self, u): return None
    async def get_by_phone(self, p): return None


class InMemoryRoleRepo:
    async def add(self, r): pass
    async def save(self, r): pass
    async def get_by_id(self, rid): return None
    async def get_by_user_id(self, uid): return []
    async def get_by_tenant_id(self, tid): return []
    async def assign_role_to_user(self, uid, rid): pass


class InMemoryMenuRepo:
    async def add(self, m): pass
    async def get_by_id(self, mid): return None
    async def get_by_role_id(self, rid): return []
    async def get_by_user_id(self, uid): return []
    async def assign_menu_to_role(self, rid, mid): pass


class InMemoryUoW:
    def __init__(self):
        self.users = InMemoryUserRepo()
        self.roles = InMemoryRoleRepo()
        self.menus = InMemoryMenuRepo()
        self.departments = InMemoryDeptRepo()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Domain model tests
# ---------------------------------------------------------------------------

def test_department_create_root() -> None:
    tenant_id = uuid4()
    dept = Department.create(tenant_id=tenant_id, name="Tech", order_num=1)
    assert dept.parent_id is None
    assert dept.ancestors == ""
    assert dept.ancestor_ids() == []


def test_department_create_child_inherits_ancestors() -> None:
    tenant_id = uuid4()
    root = Department.create(tenant_id=tenant_id, name="Company")
    child = Department.create(tenant_id=tenant_id, name="Tech", parent=root)

    assert child.parent_id == root.id
    assert str(root.id) in child.ancestors

    grandchild = Department.create(tenant_id=tenant_id, name="Backend", parent=child)
    assert str(root.id) in grandchild.ancestors
    assert str(child.id) in grandchild.ancestors


def test_department_build_child_ancestors() -> None:
    tenant_id = uuid4()
    root = Department.create(tenant_id=tenant_id, name="Root")
    # Child ancestors = root.id
    expected = str(root.id)
    assert root.build_child_ancestors() == expected

    child = Department.create(tenant_id=tenant_id, name="Child", parent=root)
    # Grandchild ancestors = root.id,child.id
    gca = child.build_child_ancestors()
    assert str(root.id) in gca
    assert str(child.id) in gca


def test_department_rename() -> None:
    d = Department.create(tenant_id=uuid4(), name="Old Name")
    old_updated = d.updated_at
    d.rename("New Name")
    assert d.name == "New Name"
    assert d.updated_at >= old_updated


# ---------------------------------------------------------------------------
# ApplicationService tests
# ---------------------------------------------------------------------------

def test_create_department_root() -> None:
    async def run():
        uow = InMemoryUoW()
        svc = UserApplicationService(uow)
        tenant_id = uuid4()
        dept = await svc.create_department(
            CreateDepartmentCommand(tenant_id=tenant_id, name="Engineering")
        )
        assert dept.name == "Engineering"
        assert dept.parent_id is None
        assert dept.ancestors == ""

    asyncio.run(run())


def test_create_department_child() -> None:
    async def run():
        uow = InMemoryUoW()
        svc = UserApplicationService(uow)
        tenant_id = uuid4()
        root = await svc.create_department(
            CreateDepartmentCommand(tenant_id=tenant_id, name="Engineering")
        )
        child = await svc.create_department(
            CreateDepartmentCommand(tenant_id=tenant_id, name="Backend", parent_id=root.id)
        )
        assert child.parent_id == root.id
        assert str(root.id) in child.ancestors

    asyncio.run(run())


def test_create_department_unknown_parent_raises() -> None:
    async def run():
        from common.errors import AppError
        uow = InMemoryUoW()
        svc = UserApplicationService(uow)
        with pytest.raises(AppError) as exc_info:
            await svc.create_department(
                CreateDepartmentCommand(tenant_id=uuid4(), name="Orphan", parent_id=uuid4())
            )
        assert exc_info.value.status_code == 404

    asyncio.run(run())


def test_delete_department_with_children_raises() -> None:
    async def run():
        from common.errors import AppError
        uow = InMemoryUoW()
        svc = UserApplicationService(uow)
        tid = uuid4()
        root = await svc.create_department(CreateDepartmentCommand(tenant_id=tid, name="Root"))
        await svc.create_department(CreateDepartmentCommand(tenant_id=tid, name="Child", parent_id=root.id))

        with pytest.raises(AppError) as exc_info:
            await svc.delete_department(root.id)
        assert exc_info.value.status_code == 409

    asyncio.run(run())


def test_update_department_rename() -> None:
    async def run():
        uow = InMemoryUoW()
        svc = UserApplicationService(uow)
        dept = await svc.create_department(CreateDepartmentCommand(tenant_id=uuid4(), name="Old"))
        updated = await svc.update_department(UpdateDepartmentCommand(dept_id=dept.id, name="New"))
        assert updated.name == "New"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Tree builder helper
# ---------------------------------------------------------------------------

def test_build_tree_nesting() -> None:
    tid = uuid4()
    root = Department.create(tenant_id=tid, name="Root")
    child = Department.create(tenant_id=tid, name="Child", parent=root)
    grandchild = Department.create(tenant_id=tid, name="GrandChild", parent=child)

    tree = _build_tree([root, child, grandchild])

    assert len(tree) == 1
    assert tree[0]["name"] == "Root"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "Child"
    assert len(tree[0]["children"][0]["children"]) == 1
    assert tree[0]["children"][0]["children"][0]["name"] == "GrandChild"


def test_build_tree_multiple_roots() -> None:
    tid = uuid4()
    r1 = Department.create(tenant_id=tid, name="A")
    r2 = Department.create(tenant_id=tid, name="B")
    tree = _build_tree([r1, r2])
    assert len(tree) == 2
