"""v5.7 security, content integrity, observability and adaptive learning

Revision ID: c57d0a31f570
Revises: b56f0c21e560
Create Date: 2026-09-07 07:35:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import hashlib
import json

revision: str = "c57d0a31f570"
down_revision: Union[str, None] = "b56f0c21e560"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _postgres_rls() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    tables = [
        "term_progress", "exam_results", "course_day_results", "gamification_profiles",
        "xp_events", "practice_results", "game_sessions", "learning_preferences",
        "notification_preferences", "learning_nudges", "srs_cards", "question_attempts",
        "pilot_daily_usage",
    ]
    policy = """(
      current_setting('app.role', true) = 'admin'
      OR user_id = NULLIF(current_setting('app.user_id', true), '')::integer
      OR (
        current_setting('app.role', true) = 'manager'
        AND EXISTS (
          SELECT 1 FROM users u
          WHERE u.id = user_id
            AND u.department = current_setting('app.department', true)
        )
      )
    )"""
    for table in tables:
        op.execute(sa.text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'DROP POLICY IF EXISTS mgc_department_scope ON {table}'))
        op.execute(sa.text(f'CREATE POLICY mgc_department_scope ON {table} USING {policy} WITH CHECK {policy}'))


def upgrade() -> None:
    op.add_column("custom_terms", sa.Column("source_type", sa.String(length=60), nullable=False, server_default="manual"))
    op.add_column("custom_terms", sa.Column("source_ref", sa.Text(), nullable=False, server_default=""))
    op.create_index(op.f("ix_custom_terms_source_type"), "custom_terms", ["source_type"], unique=False)

    op.add_column("audit_logs", sa.Column("previous_hash", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("audit_logs", sa.Column("event_hash", sa.String(length=64), nullable=False, server_default=""))
    op.create_index(op.f("ix_audit_logs_event_hash"), "audit_logs", ["event_hash"], unique=False)
    op.create_table(
        "audit_anchors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_deleted_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_deleted_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # Backfill a deterministic chain for legacy audit rows so verification starts clean after upgrade.
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id,event_type,actor_user_id,target_type,target_id,request_id,source_ip_hash,metadata_json FROM audit_logs ORDER BY id")).mappings().all()
    previous = ""
    for row in rows:
        canonical = "|".join([previous, row["event_type"] or "", str(row["actor_user_id"] or ""), row["target_type"] or "", row["target_id"] or "", row["request_id"] or "", row["source_ip_hash"] or "", row["metadata_json"] or "{}"] )
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        bind.execute(sa.text("UPDATE audit_logs SET previous_hash=:p,event_hash=:h WHERE id=:id"), {"p":previous,"h":event_hash,"id":row["id"]})
        previous = event_hash

    op.create_table(
        "term_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False, server_default="update"),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["term_id"], ["custom_terms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("term_id", "revision_no", name="uq_term_revision_no"),
    )
    op.create_index(op.f("ix_term_revisions_term_id"), "term_revisions", ["term_id"], unique=False)
    op.create_index(op.f("ix_term_revisions_created_at"), "term_revisions", ["created_at"], unique=False)
    # Existing custom terms receive revision 1 so upgrades do not start with a history gap.
    existing_terms = bind.execute(sa.text("SELECT id,language,shop,topic,subtopic,level,term,pronunciation,reading,translation,example,example_translation,tags,source_type,source_ref,status,created_by,updated_at FROM custom_terms ORDER BY id")).mappings().all()
    for row in existing_terms:
        snapshot = {k: row[k] for k in ("language","shop","topic","subtopic","level","term","pronunciation","reading","translation","example","example_translation","tags","source_type","source_ref","status")}
        bind.execute(sa.text("INSERT INTO term_revisions(term_id,revision_no,action,snapshot_json,actor_user_id,created_at) VALUES (:term_id,1,'migration_baseline',:snapshot,:actor,:created_at)"), {"term_id":row["id"],"snapshot":json.dumps(snapshot,ensure_ascii=False,sort_keys=True),"actor":row["created_by"],"created_at":row["updated_at"]})

    op.create_table(
        "term_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["term_id"], ["custom_terms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_term_reviews_term_id"), "term_reviews", ["term_id"], unique=False)
    op.create_index(op.f("ix_term_reviews_decision"), "term_reviews", ["decision"], unique=False)
    op.create_index(op.f("ix_term_reviews_created_at"), "term_reviews", ["created_at"], unique=False)

    op.create_table(
        "srs_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("term_id", sa.String(length=80), nullable=False),
        sa.Column("topic", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ease_factor_pct", sa.Integer(), nullable=False, server_default="250"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_quality", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "language", "term_id", name="uq_srs_user_language_term"),
    )
    for col in ("user_id", "language", "term_id", "topic", "due_at"):
        op.create_index(op.f(f"ix_srs_cards_{col}"), "srs_cards", [col], unique=False)

    op.create_table(
        "question_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("question_id", sa.String(length=160), nullable=False),
        sa.Column("term_id", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("topic", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="quiz"),
        sa.Column("correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("response_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "session_id", "question_id", name="uq_question_attempt_session"),
    )
    for col in ("user_id", "session_id", "question_id", "term_id", "language", "topic", "kind", "correct", "created_at"):
        op.create_index(op.f(f"ix_question_attempts_{col}"), "question_attempts", [col], unique=False)

    _postgres_rls()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ["term_progress","exam_results","course_day_results","gamification_profiles","xp_events","practice_results","game_sessions","learning_preferences","notification_preferences","learning_nudges","srs_cards","question_attempts","pilot_daily_usage"]:
            op.execute(sa.text(f'DROP POLICY IF EXISTS mgc_department_scope ON {table}'))
            op.execute(sa.text(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY'))
            op.execute(sa.text(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY'))
    for col in ("created_at","correct","kind","topic","language","term_id","question_id","session_id","user_id"):
        op.drop_index(op.f(f"ix_question_attempts_{col}"), table_name="question_attempts")
    op.drop_table("question_attempts")
    for col in ("due_at","topic","term_id","language","user_id"):
        op.drop_index(op.f(f"ix_srs_cards_{col}"), table_name="srs_cards")
    op.drop_table("srs_cards")
    op.drop_index(op.f("ix_term_reviews_created_at"), table_name="term_reviews")
    op.drop_index(op.f("ix_term_reviews_decision"), table_name="term_reviews")
    op.drop_index(op.f("ix_term_reviews_term_id"), table_name="term_reviews")
    op.drop_table("term_reviews")
    op.drop_index(op.f("ix_term_revisions_created_at"), table_name="term_revisions")
    op.drop_index(op.f("ix_term_revisions_term_id"), table_name="term_revisions")
    op.drop_table("term_revisions")
    op.drop_table("audit_anchors")
    op.drop_index(op.f("ix_audit_logs_event_hash"), table_name="audit_logs")
    op.drop_column("audit_logs", "event_hash")
    op.drop_column("audit_logs", "previous_hash")
    op.drop_index(op.f("ix_custom_terms_source_type"), table_name="custom_terms")
    op.drop_column("custom_terms", "source_ref")
    op.drop_column("custom_terms", "source_type")
