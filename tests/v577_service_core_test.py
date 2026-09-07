from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mgc.services.terminology import build_terminology_service  # noqa: E402
from mgc.services.users import build_user_service  # noqa: E402

assert "app" not in sys.modules


class Base(DeclarativeBase):
    pass


class TermProgress(Base):
    __tablename__ = "v577_progress"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20))


class ExamResult(Base):
    __tablename__ = "v577_exam"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    score: Mapped[int] = mapped_column(Integer)


class CustomTerm(Base):
    __tablename__ = "v577_custom_term"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(80), unique=True)
    language: Mapped[str] = mapped_column(String(10))
    shop: Mapped[str] = mapped_column(String(160), default="")
    topic: Mapped[str] = mapped_column(String(160))
    subtopic: Mapped[str] = mapped_column(String(160), default="")
    level: Mapped[str] = mapped_column(String(10), default="A1")
    term: Mapped[str] = mapped_column(String(500))
    pronunciation: Mapped[str] = mapped_column(String(500), default="")
    reading: Mapped[str] = mapped_column(String(500), default="")
    translation: Mapped[str] = mapped_column(String(500))
    example: Mapped[str] = mapped_column(Text, default="")
    example_translation: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(60), default="manual")
    source_ref: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TermRevision(Base):
    __tablename__ = "v577_term_revision"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(Integer, index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(30))
    snapshot_json: Mapped[str] = mapped_column(Text)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


engine = create_engine("sqlite+pysqlite:///:memory:")
Base.metadata.create_all(engine)

profile = {
    "level": 4,
    "title": "Практик I",
    "lifetime_xp": 1500,
    "spendable_xp": 120,
    "weekly_xp": 95,
    "last_activity_at": "2026-09-07T10:00:00+00:00",
}
user_service = build_user_service(
    term_progress_model=TermProgress,
    exam_result_model=ExamResult,
    gamification_view=lambda db, user_id: dict(profile),
    notification_pref=lambda db, user_id: SimpleNamespace(mode="normal"),
)

terminology_service = build_terminology_service(
    custom_term_model=CustomTerm,
    term_revision_model=TermRevision,
    base_terms={
        "english": [
            {
                "id": "base-1",
                "term": "fixture",
                "translation": "оснастка",
                "topic": "R&D",
            }
        ],
        "chinese": [],
    },
    english_pronunciation=lambda value: {"ipa": f"/{value}/", "reading": f"ru-{value}"},
    pinyin_to_ru_approx=lambda value: f"ru-{value}",
)

user = SimpleNamespace(
    id=7,
    username="engineer",
    display_name="Engineer",
    role="user",
    department="R&D",
    preferred_language="english",
    created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
)
assert user_service.user_view(user) == {
    "id": 7,
    "username": "engineer",
    "display_name": "Engineer",
    "role": "user",
    "department": "R&D",
    "preferred_language": "english",
}
assert user_service.manager_target_allowed(SimpleNamespace(role="admin", department="X"), user)
assert user_service.manager_target_allowed(SimpleNamespace(role="manager", department="R&D"), user)
assert not user_service.manager_target_allowed(SimpleNamespace(role="manager", department="Quality"), user)

with Session(engine) as db:
    db.add_all([
        TermProgress(user_id=7, status="known"),
        TermProgress(user_id=7, status="learning"),
        ExamResult(user_id=7, score=31),
        ExamResult(user_id=7, score=44),
    ])
    published = CustomTerm(
        public_id="custom-published",
        language="english",
        shop="Assembly",
        topic="Service Layer",
        term="torque audit",
        translation="контроль момента",
        status="published",
    )
    draft = CustomTerm(
        public_id="custom-draft",
        language="english",
        topic="Service Layer",
        term="draft only",
        translation="черновик",
        status="draft",
    )
    db.add_all([published, draft])
    db.flush()

    stats = user_service.user_admin_stats(db, user)
    assert stats["terms_known"] == 1
    assert stats["terms_touched"] == 2
    assert stats["best_exam"] == 44
    assert stats["level"] == 4 and stats["notification_mode"] == "normal"

    terms = terminology_service.terms_for("english", db)
    ids = [item["id"] for item in terms]
    assert ids == ["base-1", "custom-published"]
    custom = terminology_service.term_by_id("english", "custom-published", db)
    assert custom is not None
    assert custom["pronunciation"] == "/torque audit/"
    assert custom["reading"] == "ru-torque audit"
    assert terminology_service.term_by_id("english", "custom-draft", db) is None

    first = terminology_service.record_term_revision(db, published, 99, "create")
    published.translation = "проверка момента"
    second = terminology_service.record_term_revision(db, published, 99, "update")
    assert first.revision_no == 1 and second.revision_no == 2
    assert '"translation": "контроль момента"' in first.snapshot_json
    assert '"translation": "проверка момента"' in second.snapshot_json

    admin_view = terminology_service.admin_term_response(published)
    assert admin_view["db_id"] == published.id
    assert admin_view["id"] == "custom-published"
    assert admin_view["translation"] == "проверка момента"

print("OK: v5.7.7 user and terminology services preserve business helper contracts without importing app.py")
