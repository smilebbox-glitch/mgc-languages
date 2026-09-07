from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class LearningServiceBindings:
    current_week_key: Callable[..., str]
    level_info: Callable[[int], dict[str, Any]]
    get_profile: Callable[[Session, int], Any]
    gamification_view: Callable[[Session, int], dict[str, Any]]
    award_xp: Callable[..., dict[str, Any]]
    spend_xp: Callable[..., dict[str, Any]]
    get_or_create_srs_card: Callable[..., Any]
    schedule_srs: Callable[..., Any]


def build_pilot_daily_usage_accessor(
    *,
    usage_model: Any,
    day_key: Callable[[], str],
) -> Callable[[Session, int], Any]:
    """Create a race-safe per-user/day usage accessor.

    Existing rows are selected FOR UPDATE so quota increments from concurrent
    requests for the same user cannot overwrite each other. First-row creation
    is protected by a nested transaction; a unique-key loser re-fetches the
    row without rolling back the caller's outer transaction.
    """

    def pilot_daily_usage(db: Session, user_id: int) -> Any:
        key = day_key()
        stmt = select(usage_model).where(
            usage_model.user_id == user_id,
            usage_model.day_key == key,
        ).with_for_update()
        row = db.scalar(stmt)
        if row is not None:
            return row
        try:
            with db.begin_nested():
                row = usage_model(user_id=user_id, day_key=key)
                db.add(row)
                db.flush()
        except IntegrityError:
            row = db.scalar(stmt)
            if row is None:
                raise
        return row

    pilot_daily_usage.__name__ = "pilot_daily_usage"
    pilot_daily_usage.__qualname__ = "pilot_daily_usage"
    return pilot_daily_usage


def build_learning_service(
    *,
    gamification_profile_model: Any,
    xp_event_model: Any,
    srs_card_model: Any,
    pilot_daily_usage: Callable[[Session, int], Any],
    daily_xp_cap: int,
    reward_catalog: Mapping[str, Mapping[str, Any]],
    level_titles: Sequence[str],
    roman: Sequence[str],
) -> LearningServiceBindings:
    """Build the XP/profile/SRS core without importing the legacy app module."""
    if len(level_titles) < 10 or len(roman) < 10:
        raise RuntimeError("learning level title contract requires ten tiers and ten numerals")

    def current_week_key(now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        iso = now.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    def level_info(lifetime_xp: int) -> dict[str, Any]:
        level = min(100, max(1, lifetime_xp // 500 + 1))
        if level == 100:
            title = "Легенда"
            progress = 500
            needed = 500
            next_xp = None
        else:
            tier = min(9, (level - 1) // 10)
            within = (level - 1) % 10
            title = f"{level_titles[tier]} {roman[within]}"
            floor = (level - 1) * 500
            progress = lifetime_xp - floor
            needed = 500
            next_xp = level * 500
        return {
            "level": level,
            "title": title,
            "progress_xp": progress,
            "level_xp": needed,
            "next_level_xp": next_xp,
        }

    def _profile(db: Session, user_id: int, *, for_update: bool) -> Any:
        stmt = select(gamification_profile_model).where(
            gamification_profile_model.user_id == user_id
        )
        if for_update:
            stmt = stmt.with_for_update()
        profile = db.scalar(stmt)
        if profile is None:
            try:
                with db.begin_nested():
                    profile = gamification_profile_model(
                        user_id=user_id,
                        week_key=current_week_key(),
                    )
                    db.add(profile)
                    db.flush()
            except IntegrityError:
                profile = db.scalar(stmt)
                if profile is None:
                    raise
        week = current_week_key()
        if profile.week_key != week:
            profile.week_key = week
            profile.weekly_xp = 0
        return profile

    def get_profile(db: Session, user_id: int) -> Any:
        return _profile(db, user_id, for_update=False)

    def gamification_view(db: Session, user_id: int) -> dict[str, Any]:
        profile = get_profile(db, user_id)
        info = level_info(profile.lifetime_xp)
        return {
            **info,
            "lifetime_xp": profile.lifetime_xp,
            "spendable_xp": profile.spendable_xp,
            "weekly_xp": profile.weekly_xp,
            "last_activity_at": profile.last_activity_at.isoformat() if profile.last_activity_at else None,
        }

    def award_xp(
        db: Session,
        user_id: int,
        event_type: str,
        source_id: str,
        raw_xp: int,
        *,
        language: str = "",
        topic: str = "",
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        anti_farm: bool = True,
    ) -> dict[str, Any]:
        key = idempotency_key or f"{user_id}:{event_type}:{source_id}:{secrets.token_hex(6)}"
        existing = db.scalar(select(xp_event_model).where(xp_event_model.idempotency_key == key))
        if existing:
            return {"awarded": 0, "duplicate": True, "profile": gamification_view(db, user_id)}

        multiplier = 100
        if anti_farm and source_id:
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            repeat_count = len(
                db.scalars(
                    select(xp_event_model).where(
                        xp_event_model.user_id == user_id,
                        xp_event_model.event_type == event_type,
                        xp_event_model.source_id == source_id,
                        xp_event_model.created_at >= since,
                        xp_event_model.lifetime_delta > 0,
                    )
                ).all()
            )
            if repeat_count >= 6:
                multiplier = 10
            elif repeat_count >= 3:
                multiplier = 50

        awarded = max(1, round(raw_xp * multiplier / 100)) if raw_xp > 0 else 0
        usage = pilot_daily_usage(db, user_id)
        remaining = max(0, int(daily_xp_cap) - int(usage.xp_awarded or 0))
        awarded = min(awarded, remaining)
        usage.xp_awarded = int(usage.xp_awarded or 0) + awarded
        usage.updated_at = datetime.now(timezone.utc)

        # Serialize XP mutations for one user while allowing different users to
        # update in parallel. This prevents lost increments under multi-worker load.
        profile = _profile(db, user_id, for_update=True)
        profile.lifetime_xp += awarded
        profile.spendable_xp += awarded
        profile.weekly_xp += awarded
        profile.last_activity_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
        db.add(
            xp_event_model(
                user_id=user_id,
                event_type=event_type,
                source_id=source_id,
                language=language,
                topic=topic,
                xp_delta=awarded,
                lifetime_delta=awarded,
                raw_xp=raw_xp,
                multiplier_pct=multiplier,
                idempotency_key=key,
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            )
        )
        db.flush()
        return {
            "awarded": awarded,
            "duplicate": False,
            "multiplier_pct": multiplier,
            "profile": gamification_view(db, user_id),
        }

    def spend_xp(
        db: Session,
        user_id: int,
        reward_id: str,
        *,
        language: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        reward = reward_catalog.get(reward_id)
        if not reward:
            raise HTTPException(404, "Неизвестная помощь")
        profile = _profile(db, user_id, for_update=True)
        price = int(reward["price"])
        if profile.spendable_xp < price:
            raise HTTPException(
                409,
                f"Недостаточно XP: нужно {price}, доступно {profile.spendable_xp}",
            )
        profile.spendable_xp -= price
        profile.updated_at = datetime.now(timezone.utc)
        db.add(
            xp_event_model(
                user_id=user_id,
                event_type="spend",
                source_id=reward_id,
                language=language,
                topic="",
                xp_delta=-price,
                lifetime_delta=0,
                raw_xp=price,
                multiplier_pct=100,
                idempotency_key=f"spend:{user_id}:{reward_id}:{secrets.token_hex(10)}",
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            )
        )
        db.flush()
        return {"spent": price, "reward": reward, "profile": gamification_view(db, user_id)}

    def get_or_create_srs_card(
        db: Session,
        user_id: int,
        language: str,
        term_id: str,
        topic: str = "",
    ) -> Any:
        card = db.scalar(
            select(srs_card_model).where(
                srs_card_model.user_id == user_id,
                srs_card_model.language == language,
                srs_card_model.term_id == term_id,
            )
        )
        if not card:
            card = srs_card_model(
                user_id=user_id,
                language=language,
                term_id=term_id,
                topic=topic,
                due_at=datetime.now(timezone.utc),
            )
            db.add(card)
            db.flush()
        elif topic and not card.topic:
            card.topic = topic
        return card

    def schedule_srs(card: Any, quality: int, now: datetime | None = None) -> Any:
        now = now or datetime.now(timezone.utc)
        q = max(0, min(5, int(quality)))
        if q < 3:
            card.repetitions = 0
            card.lapses += 1
            card.interval_days = 1
        else:
            card.repetitions += 1
            if card.repetitions == 1:
                card.interval_days = 1
            elif card.repetitions == 2:
                card.interval_days = 3
            else:
                card.interval_days = max(
                    1,
                    round(card.interval_days * card.ease_factor_pct / 100),
                )
        ef = card.ease_factor_pct / 100.0
        ef = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        card.ease_factor_pct = int(max(130, min(300, round(ef * 100))))
        card.last_quality = q
        card.due_at = now + timedelta(days=card.interval_days)
        card.updated_at = now
        return card

    for name, fn in {
        "current_week_key": current_week_key,
        "level_info": level_info,
        "get_profile": get_profile,
        "gamification_view": gamification_view,
        "award_xp": award_xp,
        "spend_xp": spend_xp,
        "get_or_create_srs_card": get_or_create_srs_card,
        "schedule_srs": schedule_srs,
    }.items():
        fn.__name__ = name
        fn.__qualname__ = name

    return LearningServiceBindings(
        current_week_key=current_week_key,
        level_info=level_info,
        get_profile=get_profile,
        gamification_view=gamification_view,
        award_xp=award_xp,
        spend_xp=spend_xp,
        get_or_create_srs_card=get_or_create_srs_card,
        schedule_srs=schedule_srs,
    )


__all__ = [
    "LearningServiceBindings",
    "build_learning_service",
    "build_pilot_daily_usage_accessor",
]
