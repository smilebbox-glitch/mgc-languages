"""v5.2 chinese learning, audio preferences and department scope

Revision ID: c8f1a52e1a20
Revises: 78068b70afbf
Create Date: 2026-09-06 20:15:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c8f1a52e1a20"
down_revision: Union[str, None] = "78068b70afbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("department", sa.String(length=160), nullable=False, server_default="General"))
    op.create_index(op.f("ix_users_department"), "users", ["department"], unique=False)
    op.add_column("custom_terms", sa.Column("reading", sa.String(length=500), nullable=False, server_default=""))
    op.create_table(
        "learning_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("show_pinyin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_reading", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("server_audio_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("learning_preferences")
    op.drop_column("custom_terms", "reading")
    op.drop_index(op.f("ix_users_department"), table_name="users")
    op.drop_column("users", "department")
