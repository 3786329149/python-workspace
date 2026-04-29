"""create user auths table

Revision ID: 0001_create_user_auths_table
Revises:
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_user_auths_table"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_auths",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("identity_type", sa.String(length=20), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("credential", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identity_type",
            "identifier",
            name="uq_user_auths_identity",
        ),
    )
    op.create_index("ix_user_auths_user_id", "user_auths", ["user_id"], unique=False)
    op.create_index(
        "ix_user_auths_identity_type",
        "user_auths",
        ["identity_type"],
        unique=False,
    )
    op.create_index("ix_user_auths_identifier", "user_auths", ["identifier"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_auths_identifier", table_name="user_auths")
    op.drop_index("ix_user_auths_identity_type", table_name="user_auths")
    op.drop_index("ix_user_auths_user_id", table_name="user_auths")
    op.drop_table("user_auths")
