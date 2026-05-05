#!/usr/bin/env python
"""Seed script: insert complete demo data (tenants, depts, roles, users, auth).

Usage:
    uv run python scripts/seed_demo_data.py
"""
import asyncio
import sys
import bcrypt
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime, UTC

# Make sure workspace packages are importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# -- Load settings ------------------------------------------------------------
from user_service.config import settings as user_settings
from auth_service.config import settings as auth_settings

# -- Constants -----------------------------------------------------------------
SYSTEM_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_TENANT_ID   = UUID("00000000-0000-0000-0000-000000000002")

PASSWORD_PLAIN = "Pass1234"

DEMO_DEPTS = [
    {"id": UUID("11111111-1111-1111-1111-111111111111"), "tid": DEMO_TENANT_ID, "name": "演示总公司", "pid": None, "anc": ""},
    {"id": UUID("22222222-2222-2222-2222-222222222222"), "tid": DEMO_TENANT_ID, "name": "技术中心", "pid": UUID("11111111-1111-1111-1111-111111111111"), "anc": "11111111-1111-1111-1111-111111111111"},
    {"id": UUID("33333333-3333-3333-3333-333333333333"), "tid": DEMO_TENANT_ID, "name": "运营部", "pid": UUID("11111111-1111-1111-1111-111111111111"), "anc": "11111111-1111-1111-1111-111111111111"},
]

ROLES = [
    {"id": uuid4(), "name": "超级管理员", "rk": "admin", "ds": 1},
    {"id": uuid4(), "name": "普通员工", "rk": "user", "ds": 3},
]

DEMO_USERS = [
    {
        "id": UUID("00000000-0000-0000-0000-aaaaaaaaaaaa"),
        "tid": SYSTEM_TENANT_ID,
        "username": "superadmin",
        "email": "admin@system.com",
        "is_admin": True,
        "role_key": "admin",
        "dept_id": None
    },
    {
        "id": UUID("00000000-0000-0000-0000-bbbbbbbbbbbb"),
        "tid": DEMO_TENANT_ID,
        "username": "tenant_admin",
        "email": "admin@demo.com",
        "is_admin": False,
        "role_key": "admin",
        "dept_id": UUID("11111111-1111-1111-1111-111111111111")
    },
    {
        "id": UUID("00000000-0000-0000-0000-cccccccccccc"),
        "tid": DEMO_TENANT_ID,
        "username": "demo_user",
        "email": "user@demo.com",
        "is_admin": False,
        "role_key": "user",
        "dept_id": UUID("22222222-2222-2222-2222-222222222222")
    },
]

async def seed_departments(session: AsyncSession):
    now = datetime.now(UTC)
    for d in DEMO_DEPTS:
        row = await session.execute(text("SELECT 1 FROM departments WHERE id = :id"), {"id": str(d["id"])})
        if not row.fetchone():
            await session.execute(
                text("INSERT INTO departments (id, tenant_id, name, parent_id, ancestors, order_num, created_at, updated_at) "
                     "VALUES (:id, :tid, :name, :pid, :anc, 0, :ca, :ua)"),
                {"id": str(d["id"]), "tid": str(d["tid"]), "name": d["name"], "pid": str(d["pid"]) if d["pid"] else None, "anc": d["anc"], "ca": now, "ua": now}
            )
            print(f"  [insert] dept '{d['name']}'")

async def seed_roles_and_users(user_session: AsyncSession, auth_session: AsyncSession):
    now = datetime.now(UTC)
    salt = bcrypt.gensalt()
    hashed_pwd = bcrypt.hashpw(PASSWORD_PLAIN.encode('utf-8'), salt).decode('utf-8')
    
    # Ensure roles exist in both tenants
    role_id_map = {} # (tid, rk) -> id
    for tid in [SYSTEM_TENANT_ID, DEMO_TENANT_ID]:
        for r in ROLES:
            row = await user_session.execute(text("SELECT id FROM roles WHERE tenant_id = :tid AND role_key = :rk"), {"tid": str(tid), "rk": r["rk"]})
            existing = row.fetchone()
            if existing:
                rid = UUID(str(existing[0]))
                role_id_map[(tid, r["rk"])] = rid
            else:
                rid = uuid4()
                await user_session.execute(
                    text("INSERT INTO roles (id, tenant_id, name, role_key, data_scope, created_at, updated_at) "
                         "VALUES (:id, :tid, :name, :rk, :ds, :ca, :ua)"),
                    {"id": str(rid), "tid": str(tid), "name": r["name"], "rk": r["rk"], "ds": r["ds"], "ca": now, "ua": now}
                )
                role_id_map[(tid, r["rk"])] = rid
                print(f"  [insert] role '{r['rk']}' for tenant {tid}")

    # Seed users
    for u in DEMO_USERS:
        # User record
        row = await user_session.execute(text("SELECT 1 FROM users WHERE id = :id"), {"id": str(u["id"])})
        if not row.fetchone():
            await user_session.execute(
                text("INSERT INTO users (id, tenant_id, email, username, status, is_admin, dept_id, created_at, updated_at) "
                     "VALUES (:id, :tid, :email, :un, 'active', :admin, :did, :ca, :ua)"),
                {"id": str(u["id"]), "tid": str(u["tid"]), "email": u["email"], "un": u["username"], "admin": u["is_admin"], "did": str(u["dept_id"]) if u["dept_id"] else None, "ca": now, "ua": now}
            )
            # Bind role
            rid = role_id_map[(u["tid"], u["role_key"])]
            await user_session.execute(
                text("INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"),
                {"uid": str(u["id"]), "rid": str(rid)}
            )
            print(f"  [insert] user '{u['username']}'")
        
        # Auth record
        row = await auth_session.execute(text("SELECT 1 FROM user_auths WHERE user_id = :uid"), {"uid": str(u["id"])})
        if not row.fetchone():
            await auth_session.execute(
                text("INSERT INTO user_auths (id, user_id, identity_type, identifier, credential, created_at, updated_at) "
                     "VALUES (:id, :uid, 'password', :un, :pwd, :ca, :ua)"),
                {"id": str(uuid4()), "uid": str(u["id"]), "un": u["username"], "pwd": hashed_pwd, "ca": now, "ua": now}
            )
            print(f"  [insert] auth for '{u['username']}'")

async def main():
    user_engine = create_async_engine(user_settings.async_db_url)
    auth_engine = create_async_engine(auth_settings.async_db_url)
    
    user_session_factory = async_sessionmaker(user_engine, expire_on_commit=False)
    auth_session_factory = async_sessionmaker(auth_engine, expire_on_commit=False)

    print("\n=== Seeding Demo Data ===\n")
    
    async with user_session_factory() as user_session:
        async with user_session.begin():
            print("Departments:")
            await seed_departments(user_session)
            
            print("\nUsers & Roles (User DB):")
            async with auth_session_factory() as auth_session:
                async with auth_session.begin():
                    print("Auth credentials (Auth DB):")
                    await seed_roles_and_users(user_session, auth_session)

    await user_engine.dispose()
    await auth_engine.dispose()
    print("\n✅ Demo data seed complete.\n")

if __name__ == "__main__":
    asyncio.run(main())
