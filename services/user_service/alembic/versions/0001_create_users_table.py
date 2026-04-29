"""create users table

Revision ID: 0001_create_users_table
Revises:
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_users_table"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("ancestors", sa.Text(), nullable=True),
        sa.Column("order_num", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"], unique=False)
    op.create_index("ix_departments_tenant_id", "departments", ["tenant_id"], unique=False)

    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("role_key", sa.String(length=50), nullable=False),
        sa.Column("data_scope", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_role_key", "roles", ["role_key"], unique=False)
    op.create_index("ix_roles_tenant_id", "roles", ["tenant_id"], unique=False)

    op.create_table(
        "menus",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("menu_name", sa.String(length=50), nullable=False),
        sa.Column("menu_type", sa.String(length=1), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("perms", sa.String(length=100), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("order_num", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["menus.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_menus_parent_id", "menus", ["parent_id"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("nickname", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("dept_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["dept_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_dept_id", "users", ["dept_id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_status", "users", ["status"], unique=False)

    op.create_table(
        "role_menus",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("menu_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["menu_id"], ["menus.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("role_id", "menu_id"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("role_menus")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_dept_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_menus_parent_id", table_name="menus")
    op.drop_table("menus")
    op.drop_index("ix_roles_tenant_id", table_name="roles")
    op.drop_index("ix_roles_role_key", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_departments_tenant_id", table_name="departments")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_table("departments")
