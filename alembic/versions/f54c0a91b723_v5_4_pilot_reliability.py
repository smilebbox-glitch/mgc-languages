"""v5.4 pilot reliability operational telemetry

Revision ID: f54c0a91b723
Revises: c8f1a52e1a20
Create Date: 2026-09-07 00:05:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "f54c0a91b723"
down_revision: Union[str, None] = "c8f1a52e1a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="warning"),
        sa.Column("component", sa.String(length=60), nullable=False, server_default="app"),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("path", sa.String(length=240), nullable=False, server_default=""),
        sa.Column("detail", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operational_events_event_type"), "operational_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_operational_events_severity"), "operational_events", ["severity"], unique=False)
    op.create_index(op.f("ix_operational_events_component"), "operational_events", ["component"], unique=False)
    op.create_index(op.f("ix_operational_events_request_id"), "operational_events", ["request_id"], unique=False)
    op.create_index(op.f("ix_operational_events_created_at"), "operational_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operational_events_created_at"), table_name="operational_events")
    op.drop_index(op.f("ix_operational_events_request_id"), table_name="operational_events")
    op.drop_index(op.f("ix_operational_events_component"), table_name="operational_events")
    op.drop_index(op.f("ix_operational_events_severity"), table_name="operational_events")
    op.drop_index(op.f("ix_operational_events_event_type"), table_name="operational_events")
    op.drop_table("operational_events")
