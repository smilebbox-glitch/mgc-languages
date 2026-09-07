"""v5.5 pilot operations alerts

Revision ID: a55c0b91d550
Revises: f54c0a91b723
Create Date: 2026-09-07 00:40:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a55c0b91d550"
down_revision: Union[str, None] = "f54c0a91b723"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pilot_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_key", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("component", sa.String(length=60), nullable=False, server_default="app"),
        sa.Column("title", sa.String(length=220), nullable=False, server_default=""),
        sa.Column("detail", sa.String(length=700), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_key"),
    )
    op.create_index(op.f("ix_pilot_alerts_alert_key"), "pilot_alerts", ["alert_key"], unique=True)
    op.create_index(op.f("ix_pilot_alerts_severity"), "pilot_alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_pilot_alerts_status"), "pilot_alerts", ["status"], unique=False)
    op.create_index(op.f("ix_pilot_alerts_component"), "pilot_alerts", ["component"], unique=False)
    op.create_index(op.f("ix_pilot_alerts_first_seen_at"), "pilot_alerts", ["first_seen_at"], unique=False)
    op.create_index(op.f("ix_pilot_alerts_last_seen_at"), "pilot_alerts", ["last_seen_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pilot_alerts_last_seen_at"), table_name="pilot_alerts")
    op.drop_index(op.f("ix_pilot_alerts_first_seen_at"), table_name="pilot_alerts")
    op.drop_index(op.f("ix_pilot_alerts_component"), table_name="pilot_alerts")
    op.drop_index(op.f("ix_pilot_alerts_status"), table_name="pilot_alerts")
    op.drop_index(op.f("ix_pilot_alerts_severity"), table_name="pilot_alerts")
    op.drop_index(op.f("ix_pilot_alerts_alert_key"), table_name="pilot_alerts")
    op.drop_table("pilot_alerts")
