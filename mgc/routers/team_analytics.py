from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from mgc.routers.shift_analytics import DIMENSIONS, FACTORY_METRICS, SHIFT_KIND, decode_shift_topic


TEAM_TRAINING = {
    "production_control": "Shift Simulation + Quality Gate",
    "prioritization": "Shift Simulation + Shift Incident",
    "production_judgement": "Quality Gate + Spec or NOK? + Shift Incident",
    "language": "Dialogue Duel + Phrase Builder",
}
FACTORY_TRAINING = {
    "line": "Andon / containment / restart criteria",
    "quality": "suspect window / traceability / first-off",
    "material": "run-out / approved stock / sequencing / fallback",
    "supplier": "part-lot-quantity / ETA / owner / deadline / evidence",
    "load": "owner / checkpoint / structured handover",
}


def _duration_ms(started: Any, completed: Any) -> int | None:
    if not started or not completed:
        return None
    try:
        value = int((completed - started).total_seconds() * 1000)
    except Exception:
        return None
    return max(0, value)


def _best_rows(rows: list[tuple[Any, Any]], current_user_id: int) -> tuple[list[dict[str, Any]], int | None]:
    best: dict[int, dict[str, Any]] = {}
    for session, person in rows:
        duration = _duration_ms(session.created_at, session.completed_at)
        if duration is None:
            continue
        item = {
            "user_id": int(session.user_id),
            "display_name": str(person.display_name),
            "score": int(session.score or 0),
            "total": int(session.total or 0),
            "duration_ms": duration,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }
        previous = best.get(item["user_id"])
        if previous is None or (-item["score"], item["duration_ms"]) < (-previous["score"], previous["duration_ms"]):
            best[item["user_id"]] = item
    ordered = sorted(best.values(), key=lambda x: (-x["score"], x["duration_ms"], x["display_name"].lower()))
    current_position = None
    for index, item in enumerate(ordered, start=1):
        if item["user_id"] == current_user_id:
            current_position = index
        item["rank"] = index
        item["is_current_user"] = item["user_id"] == current_user_id
        item.pop("user_id", None)
    return ordered, current_position


def summarize_team_shift_rows(rows: list[tuple[Any, Any]], eligible_users: int) -> dict[str, Any]:
    by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    language_mix: Counter[str] = Counter()
    for row, _person in rows:
        detail = decode_shift_topic(row.topic)
        item = {"total_score": int(row.score or 0), **detail}
        by_user[int(row.user_id)].append(item)
        language_mix[str(row.language)] += 1

    user_summaries: list[dict[str, Any]] = []
    for items in by_user.values():
        recent = items[:20]
        averages = {key: round(sum(int(x.get(key, 0)) for x in recent) / max(1, len(recent))) for key in DIMENSIONS}
        factory: dict[str, int] = {}
        for key in FACTORY_METRICS:
            values = [int((x.get("final_metrics") or {}).get(key, 0)) for x in recent]
            health = [100 - value if key == "load" else value for value in values]
            factory[key] = round(sum(health) / max(1, len(health)))
        user_summaries.append({"averages": averages, "factory": factory})

    if user_summaries:
        team_averages = {
            key: round(sum(x["averages"][key] for x in user_summaries) / len(user_summaries))
            for key in DIMENSIONS
        }
        factory_health = {
            key: round(sum(x["factory"][key] for x in user_summaries) / len(user_summaries))
            for key in FACTORY_METRICS
        }
        weakest_dimension = min(DIMENSIONS, key=lambda key: team_averages[key])
        weakest_factory = min(FACTORY_METRICS, key=lambda key: factory_health[key])
    else:
        team_averages = {key: None for key in DIMENSIONS}
        factory_health = {key: None for key in FACTORY_METRICS}
        weakest_dimension = None
        weakest_factory = None

    return {
        "eligible_users": int(eligible_users),
        "participants": len(by_user),
        "completed_shifts": len(rows),
        "participation_percent": round(len(by_user) * 100 / max(1, eligible_users)),
        "averages": team_averages,
        "factory_health": factory_health,
        "weakest_dimension": weakest_dimension,
        "weakest_factory": weakest_factory,
        "language_mix": {"chinese": int(language_mix.get("chinese", 0)), "english": int(language_mix.get("english", 0))},
        "recommended_training": TEAM_TRAINING.get(weakest_dimension or ""),
        "factory_training": FACTORY_TRAINING.get(weakest_factory or ""),
    }


def build_team_analytics_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    require_roles: Callable[..., Callable[..., Any]],
    user_model: Any,
    practice_result_model: Any,
    game_session_model: Any,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/manager/shift-analytics")
    def manager_shift_analytics(
        department: str | None = Query(default=None, max_length=160),
        language: str | None = Query(default=None),
        user: Any = Depends(require_roles("manager", "admin")),
        db: Session = Depends(db_session),
    ):
        requested = (department or "").strip()
        if user.role == "manager" and requested and requested != user.department:
            raise HTTPException(403, "Руководитель может видеть агрегаты только своего подразделения")
        scope = str(user.department) if user.role == "manager" else (requested or None)
        users_query = select(user_model).order_by(user_model.display_name)
        if scope:
            users_query = users_query.where(user_model.department == scope)
        people = list(db.scalars(users_query).all())
        user_ids = [int(row.id) for row in people]
        rows: list[tuple[Any, Any]] = []
        if user_ids:
            result_query = (
                select(practice_result_model, user_model)
                .join(user_model, user_model.id == practice_result_model.user_id)
                .where(
                    practice_result_model.user_id.in_(user_ids),
                    practice_result_model.kind == SHIFT_KIND,
                )
                .order_by(practice_result_model.created_at.desc())
                .limit(2000)
            )
            if language in {"chinese", "english"}:
                result_query = result_query.where(practice_result_model.language == language)
            rows = list(db.execute(result_query).all())
        return {
            "department": scope or "ALL",
            "summary": summarize_team_shift_rows(rows, len(people)),
            "note": "Учебная агрегированная аналитика подразделения; не является HR-рейтингом или оценкой профессиональной пригодности.",
        }

    @router.get("/api/leaderboards/games/{game_type}")
    def game_leaderboard(
        game_type: str,
        language: str = Query(default="chinese"),
        topic: str = Query(default="", max_length=160),
        limit: int = Query(default=10, ge=1, le=10),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        query = (
            select(game_session_model, user_model)
            .join(user_model, user_model.id == game_session_model.user_id)
            .where(
                user_model.department == user.department,
                game_session_model.status == "completed",
                game_session_model.game_type == game_type,
                game_session_model.language == language,
            )
            .order_by(game_session_model.completed_at.desc())
            .limit(1000)
        )
        if topic:
            query = query.where(game_session_model.topic == topic)
        ordered, current_position = _best_rows(list(db.execute(query).all()), int(user.id))
        return {
            "scope": "department",
            "department": str(user.department),
            "game_type": game_type,
            "language": language,
            "topic": topic,
            "ranking": ordered[:limit],
            "current_position": current_position,
            "rule": "score_desc_then_time_asc_best_attempt_per_user",
        }

    @router.get("/api/leaderboards/shifts")
    def shift_leaderboard(
        language: str = Query(default="chinese"),
        limit: int = Query(default=10, ge=1, le=10),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        rows = list(db.execute(
            select(practice_result_model, user_model)
            .join(user_model, user_model.id == practice_result_model.user_id)
            .where(
                user_model.department == user.department,
                practice_result_model.kind == SHIFT_KIND,
                practice_result_model.language == language,
            )
            .order_by(practice_result_model.created_at.desc())
            .limit(1000)
        ).all())
        best: dict[int, dict[str, Any]] = {}
        for row, person in rows:
            detail = decode_shift_topic(row.topic)
            duration = detail.get("duration_ms")
            if duration is None:
                continue
            item = {
                "user_id": int(row.user_id), "display_name": str(person.display_name),
                "score": int(row.score or 0), "total": 100, "duration_ms": int(duration),
                "completed_at": row.created_at.isoformat() if row.created_at else None,
            }
            previous = best.get(item["user_id"])
            if previous is None or (-item["score"], item["duration_ms"]) < (-previous["score"], previous["duration_ms"]):
                best[item["user_id"]] = item
        ordered = sorted(best.values(), key=lambda x: (-x["score"], x["duration_ms"], x["display_name"].lower()))
        current_position = None
        for index, item in enumerate(ordered, start=1):
            if item["user_id"] == int(user.id):
                current_position = index
            item["rank"] = index
            item["is_current_user"] = item["user_id"] == int(user.id)
            item.pop("user_id", None)
        return {
            "scope": "department", "department": str(user.department), "language": language,
            "ranking": ordered[:limit], "current_position": current_position,
            "rule": "score_desc_then_time_asc_best_attempt_per_user",
        }

    return router


__all__ = ["build_team_analytics_router", "summarize_team_shift_rows"]
