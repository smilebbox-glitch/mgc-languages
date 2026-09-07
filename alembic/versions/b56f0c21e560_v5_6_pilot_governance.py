"""v5.6 pilot governance and rollout

Revision ID: b56f0c21e560
Revises: a55c0b91d550
Create Date: 2026-09-07 06:55:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b56f0c21e560"
down_revision: Union[str, None] = "a55c0b91d550"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pilot_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("department", sa.String(length=160), nullable=False, server_default="General"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("wave", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    for col in ("name", "department", "status", "wave"):
        op.create_index(op.f(f"ix_pilot_groups_{col}"), "pilot_groups", [col], unique=(col == "name"))

    op.create_table(
        "pilot_group_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["pilot_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_pilot_group_member"),
    )
    op.create_index(op.f("ix_pilot_group_members_group_id"), "pilot_group_members", ["group_id"], unique=False)
    op.create_index(op.f("ix_pilot_group_members_user_id"), "pilot_group_members", ["user_id"], unique=False)

    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flag_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag_key"),
    )
    op.create_index(op.f("ix_feature_flags_flag_key"), "feature_flags", ["flag_key"], unique=True)

    op.create_table(
        "pilot_group_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("flag_key", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["pilot_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "flag_key", name="uq_pilot_group_feature"),
    )
    op.create_index(op.f("ix_pilot_group_features_group_id"), "pilot_group_features", ["group_id"], unique=False)
    op.create_index(op.f("ix_pilot_group_features_flag_key"), "pilot_group_features", ["flag_key"], unique=False)

    op.create_table(
        "pilot_track_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("track_name", sa.String(length=180), nullable=False),
        sa.Column("topic", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("target_level", sa.String(length=10), nullable=False, server_default="A1"),
        sa.Column("due_date", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["pilot_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pilot_track_assignments_group_id"), "pilot_track_assignments", ["group_id"], unique=False)
    op.create_index(op.f("ix_pilot_track_assignments_language"), "pilot_track_assignments", ["language"], unique=False)

    op.create_table(
        "pilot_daily_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day_key", sa.String(length=10), nullable=False),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("game_starts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tts_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("practice_submissions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "day_key", name="uq_pilot_daily_usage"),
    )
    op.create_index(op.f("ix_pilot_daily_usage_user_id"), "pilot_daily_usage", ["user_id"], unique=False)
    op.create_index(op.f("ix_pilot_daily_usage_day_key"), "pilot_daily_usage", ["day_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pilot_daily_usage_day_key"), table_name="pilot_daily_usage")
    op.drop_index(op.f("ix_pilot_daily_usage_user_id"), table_name="pilot_daily_usage")
    op.drop_table("pilot_daily_usage")
    op.drop_index(op.f("ix_pilot_track_assignments_language"), table_name="pilot_track_assignments")
    op.drop_index(op.f("ix_pilot_track_assignments_group_id"), table_name="pilot_track_assignments")
    op.drop_table("pilot_track_assignments")
    op.drop_index(op.f("ix_pilot_group_features_flag_key"), table_name="pilot_group_features")
    op.drop_index(op.f("ix_pilot_group_features_group_id"), table_name="pilot_group_features")
    op.drop_table("pilot_group_features")
    op.drop_index(op.f("ix_feature_flags_flag_key"), table_name="feature_flags")
    op.drop_table("feature_flags")
    op.drop_index(op.f("ix_pilot_group_members_user_id"), table_name="pilot_group_members")
    op.drop_index(op.f("ix_pilot_group_members_group_id"), table_name="pilot_group_members")
    op.drop_table("pilot_group_members")
    for col in ("wave", "status", "department", "name"):
        op.drop_index(op.f(f"ix_pilot_groups_{col}"), table_name="pilot_groups")
    op.drop_table("pilot_groups")
