#!/usr/bin/env python
"""Seed script: insert default roles and permission menus into user_service DB.

Usage:
    uv run python scripts/seed_rbac.py

The script is idempotent — safe to run multiple times.

Default data inserted:
    Roles (tenant_id = SYSTEM_TENANT_ID):
        admin   - 管理员 (data_scope=1, all data)
        user    - 普通用户 (data_scope=3, own data only)

    Menus / permission-points (menu_type=F):
        user:list    - 查看用户列表
        user:create  - 创建用户
        user:edit    - 编辑用户
        user:delete  - 删除用户
        role:list    - 查看角色列表
        role:assign  - 分配角色

    Role-Menu bindings:
        admin → all permissions
        user  → user:list (read-only)
"""
import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, UTC

# Make sure workspace packages are importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ── Load settings ────────────────────────────────────────────────────────────
from user_service.config import settings  # noqa: E402

# ── Constants ─────────────────────────────────────────────────────────────────
# A fixed "system" tenant UUID used for built-in roles/menus.
# In a multi-tenant setup each real tenant creates their own roles.
SYSTEM_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")

ROLES = [
    {"name": "管理员", "role_key": "admin", "data_scope": 1},
    {"name": "普通用户", "role_key": "user", "data_scope": 3},
]

MENUS = [
    {"menu_name": "查看用户列表",   "perms": "user:list"},
    {"menu_name": "创建用户",       "perms": "user:create"},
    {"menu_name": "编辑用户",       "perms": "user:edit"},
    {"menu_name": "删除用户",       "perms": "user:delete"},
    {"menu_name": "查看角色列表",   "perms": "role:list"},
    {"menu_name": "分配角色",       "perms": "role:assign"},
]

# admin gets every permission; user gets read-only
ADMIN_PERMS = {"user:list", "user:create", "user:edit", "user:delete", "role:list", "role:assign"}
USER_PERMS  = {"user:list"}


async def _upsert_roles(session: AsyncSession) -> dict[str, UUID]:
    """Insert roles if they don't exist; return {role_key: role_id}."""
    now = datetime.now(UTC)
    result: dict[str, UUID] = {}
    for r in ROLES:
        row = await session.execute(
            text("SELECT id FROM roles WHERE role_key = :rk AND tenant_id = :tid"),
            {"rk": r["role_key"], "tid": str(SYSTEM_TENANT_ID)},
        )
        existing = row.fetchone()
        if existing:
            result[r["role_key"]] = UUID(str(existing[0]))
            print(f"  [skip] role '{r['role_key']}' already exists")
        else:
            role_id = uuid4()
            await session.execute(
                text(
                    "INSERT INTO roles (id, tenant_id, name, role_key, data_scope, created_at, updated_at) "
                    "VALUES (:id, :tid, :name, :rk, :ds, :ca, :ua)"
                ),
                {
                    "id": str(role_id),
                    "tid": str(SYSTEM_TENANT_ID),
                    "name": r["name"],
                    "rk": r["role_key"],
                    "ds": r["data_scope"],
                    "ca": now,
                    "ua": now,
                },
            )
            result[r["role_key"]] = role_id
            print(f"  [insert] role '{r['role_key']}' → {role_id}")
    return result


async def _upsert_menus(session: AsyncSession) -> dict[str, UUID]:
    """Insert menu/permission-point rows; return {perms: menu_id}."""
    now = datetime.now(UTC)
    result: dict[str, UUID] = {}
    for m in MENUS:
        row = await session.execute(
            text("SELECT id FROM menus WHERE perms = :p AND menu_type = 'F'"),
            {"p": m["perms"]},
        )
        existing = row.fetchone()
        if existing:
            result[m["perms"]] = UUID(str(existing[0]))
            print(f"  [skip] menu '{m['perms']}' already exists")
        else:
            menu_id = uuid4()
            await session.execute(
                text(
                    "INSERT INTO menus (id, parent_id, menu_name, menu_type, path, perms, icon, order_num, created_at, updated_at) "
                    "VALUES (:id, NULL, :mn, 'F', NULL, :p, NULL, 0, :ca, :ua)"
                ),
                {"id": str(menu_id), "mn": m["menu_name"], "p": m["perms"], "ca": now, "ua": now},
            )
            result[m["perms"]] = menu_id
            print(f"  [insert] menu '{m['perms']}' → {menu_id}")
    return result


async def _bind_role_menus(
    session: AsyncSession,
    role_map: dict[str, UUID],
    menu_map: dict[str, UUID],
) -> None:
    """Bind menus to roles; skip existing bindings."""
    bindings: dict[str, set[str]] = {
        "admin": ADMIN_PERMS,
        "user": USER_PERMS,
    }
    for role_key, perms in bindings.items():
        role_id = role_map[role_key]
        for perm in sorted(perms):
            menu_id = menu_map[perm]
            row = await session.execute(
                text("SELECT 1 FROM role_menus WHERE role_id = :rid AND menu_id = :mid"),
                {"rid": str(role_id), "mid": str(menu_id)},
            )
            if row.fetchone():
                print(f"  [skip] role_menu {role_key} → {perm}")
            else:
                await session.execute(
                    text("INSERT INTO role_menus (role_id, menu_id) VALUES (:rid, :mid)"),
                    {"rid": str(role_id), "mid": str(menu_id)},
                )
                print(f"  [insert] role_menu {role_key} → {perm}")


async def main() -> None:
    engine = create_async_engine(settings.async_db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print(f"\n=== Seeding RBAC data into {settings.async_db_url!r} ===\n")
    async with session_factory() as session:
        async with session.begin():
            print("Roles:")
            role_map = await _upsert_roles(session)
            print("\nMenus / permission-points:")
            menu_map = await _upsert_menus(session)
            print("\nRole-Menu bindings:")
            await _bind_role_menus(session, role_map, menu_map)

    await engine.dispose()
    print("\n✅ Seed complete.\n")
    print("Summary:")
    print(f"  SYSTEM_TENANT_ID = {SYSTEM_TENANT_ID}")
    for rk, rid in role_map.items():
        print(f"  role '{rk}' id = {rid}")


if __name__ == "__main__":
    asyncio.run(main())
