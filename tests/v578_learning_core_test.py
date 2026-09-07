from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select  # noqa: E402
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column  # noqa: E402

from mgc.services.learning import build_learning_service  # noqa: E402


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lifetime_xp: Mapped[int] = mapped_column(Integer, default=0)
    spendable_xp: Mapped[int] = mapped_column(Integer, default=0)
    weekly_xp: Mapped[int] = mapped_column(Integer, default=0)
    week_key: Mapped[str] = mapped_column(String(12), default="")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class XPEvent(Base):
    __tablename__ = "xp_events_test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    source_id: Mapped[str] = mapped_column(String(160), default="", index=True)
    language: Mapped[str] = mapped_column(String(10), default="")
    topic: Mapped[str] = mapped_column(String(160), default="")
    xp_delta: Mapped[int] = mapped_column(Integer)
    lifetime_delta: Mapped[int] = mapped_column(Integer, default=0)
    raw_xp: Mapped[int] = mapped_column(Integer, default=0)
    multiplier_pct: Mapped[int] = mapped_column(Integer, default=100)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    language: Mapped[str] = mapped_column(String(10), index=True)
    term_id: Mapped[str] = mapped_column(String(80), index=True)
    topic: Mapped[str] = mapped_column(String(160), default="")
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    ease_factor_pct: Mapped[int] = mapped_column(Integer, default=250)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_quality: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Usage(Base):
    __tablename__ = "usage"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


engine = create_engine("sqlite+pysqlite:///:memory:")
Base.metadata.create_all(engine)


def pilot_daily_usage(db: Session, user_id: int) -> Usage:
    row = db.get(Usage, user_id)
    if not row:
        row = Usage(user_id=user_id)
        db.add(row)
        db.flush()
    return row


bindings = build_learning_service(
    gamification_profile_model=Profile,
    xp_event_model=XPEvent,
    srs_card_model=Card,
    pilot_daily_usage=pilot_daily_usage,
    daily_xp_cap=1000,
    reward_catalog={"hint_small": {"title": "Небольшая подсказка", "price": 10}},
    level_titles=("Новичок", "Ученик", "Практик", "Специалист", "Уверенный", "Профессионал", "Наставник", "Эксперт", "Мастер", "Грандмастер"),
    roman=("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"),
)

assert bindings.level_info(0)["level"] == 1
assert bindings.level_info(0)["title"] == "Новичок I"
assert bindings.level_info(500)["level"] == 2
assert bindings.level_info(49_500)["level"] == 100
assert bindings.level_info(49_500)["title"] == "Легенда"
assert bindings.level_info(49_500)["next_level_xp"] is None

with Session(engine) as db:
    first = bindings.award_xp(db, 7, "quiz", "same-source", 20, idempotency_key="event-1")
    assert first["awarded"] == 20 and first["multiplier_pct"] == 100
    duplicate = bindings.award_xp(db, 7, "quiz", "same-source", 20, idempotency_key="event-1")
    assert duplicate["duplicate"] is True and duplicate["awarded"] == 0

    multipliers = []
    for index in range(2, 8):
        result = bindings.award_xp(db, 7, "quiz", "same-source", 20, idempotency_key=f"event-{index}")
        multipliers.append(result["multiplier_pct"])
    assert multipliers == [100, 100, 50, 50, 50, 10]

    before_spend = bindings.gamification_view(db, 7)
    spent = bindings.spend_xp(db, 7, "hint_small")
    assert spent["spent"] == 10
    assert spent["profile"]["lifetime_xp"] == before_spend["lifetime_xp"]
    assert spent["profile"]["spendable_xp"] == before_spend["spendable_xp"] - 10

    events = db.scalars(select(XPEvent).where(XPEvent.user_id == 7)).all()
    assert any(row.event_type == "spend" and row.lifetime_delta == 0 for row in events)

    card = bindings.get_or_create_srs_card(db, 7, "chinese", "term-1", "Сварка")
    same = bindings.get_or_create_srs_card(db, 7, "chinese", "term-1", "Сварка")
    assert same.id == card.id
    anchor = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
    bindings.schedule_srs(card, 5, anchor)
    assert card.repetitions == 1 and card.interval_days == 1 and card.ease_factor_pct == 260
    bindings.schedule_srs(card, 5, anchor)
    assert card.repetitions == 2 and card.interval_days == 3 and card.ease_factor_pct == 270
    bindings.schedule_srs(card, 5, anchor)
    assert card.repetitions == 3 and card.interval_days == 8 and card.ease_factor_pct == 280
    bindings.schedule_srs(card, 1, anchor)
    assert card.repetitions == 0 and card.lapses == 1 and card.interval_days == 1 and card.ease_factor_pct == 226

assert bindings.award_xp.__module__ == "mgc.services.learning"
assert bindings.schedule_srs.__module__ == "mgc.services.learning"
print("OK: v5.7.8 learning core preserves levels, XP idempotency/anti-farm/spending and SM2-inspired SRS semantics")
