from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Iterable

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .shift_analytics import SHIFT_KIND, decode_shift_topic


SKILLS: dict[str, dict[str, Any]] = {
    "vocabulary": {"label": "Терминология", "games": ("match", "mistake", "memory_pairs", "odd_one_out", "rapid_recall")},
    "listening": {"label": "Аудирование", "games": ("listening", "rapid_recall", "dialogue_choice")},
    "production": {"label": "Производство", "games": ("assembly_order", "shop_route", "tool_select", "hotspot")},
    "quality": {"label": "Качество", "games": ("defect_detective", "quality_gate", "spec_check", "safety_spot")},
    "logistics": {"label": "Логистика", "games": ("logistics_route", "kanban", "shop_route", "shift_incident")},
    "engineering": {"label": "Инженерия", "games": ("bom_builder", "hotspot", "spec_check", "assembly_order")},
    "communication": {"label": "Коммуникация", "games": ("dialogue_choice", "phrase", "shift_incident", "listening")},
}

GAME_TITLES = {
    "match": "Word Match", "listening": "Listening Sprint", "mistake": "Precision Check",
    "phrase": "Phrase Builder", "hotspot": "Car Part Hotspot", "assembly_order": "Build the Car",
    "shop_route": "Factory Router", "tool_select": "Tool Selector", "defect_detective": "Defect Detective",
    "safety_spot": "Safety Spot", "quality_gate": "Quality Gate", "logistics_route": "Logistics Flow",
    "kanban": "Kanban Challenge", "bom_builder": "Build the BOM", "spec_check": "Spec or NOK?",
    "rapid_recall": "10-Second Recall", "memory_pairs": "Memory Garage", "odd_one_out": "Odd One Out",
    "dialogue_choice": "Dialogue Duel", "shift_incident": "Shift Incident",
}

SHIFT_PRESSURE = {
    "production_control": ("production", "quality"),
    "prioritization": ("logistics", "production"),
    "production_judgement": ("quality", "engineering"),
    "language": ("communication", "listening", "vocabulary"),
}
FACTORY_PRESSURE = {
    "line": ("production", "quality"),
    "quality": ("quality", "engineering"),
    "material": ("logistics", "production"),
    "supplier": ("communication", "logistics"),
    "load": ("communication", "production"),
}


def _percent(score: Any, total: Any) -> int:
    try:
        denominator = max(1, int(total or 0))
        return max(0, min(100, round(int(score or 0) * 100 / denominator)))
    except (TypeError, ValueError):
        return 0


def _game_stats(rows: Iterable[Any]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    by_game: dict[str, list[int]] = defaultdict(list)
    order: list[str] = []
    for row in rows:
        game_type = str(getattr(row, "game_type", "") or "")
        if not game_type:
            continue
        by_game[game_type].append(_percent(getattr(row, "score", 0), getattr(row, "total", 0)))
        order.append(game_type)

    stats: dict[str, dict[str, Any]] = {}
    recency: dict[str, int] = {}
    for index, game_type in enumerate(order):
        recency.setdefault(game_type, index)
    for game_type, values in by_game.items():
        recent = values[:5]
        stats[game_type] = {
            "attempts": len(values),
            "recent_average": round(sum(recent) / max(1, len(recent))),
            "best": max(values),
        }
    return stats, recency


def _skill_scores(rows: Iterable[Any]) -> tuple[dict[str, int], dict[str, dict[str, Any]], dict[str, int]]:
    rows = list(rows)
    stats, recency = _game_stats(rows)
    scores: dict[str, int] = {}
    for skill, meta in SKILLS.items():
        games = tuple(meta["games"])
        tested = [stats[game]["recent_average"] for game in games if game in stats]
        coverage = sum(1 for game in games if game in stats) / max(1, len(games))
        if tested:
            scores[skill] = round((sum(tested) / len(tested)) * 0.8 + coverage * 100 * 0.2)
        else:
            scores[skill] = 45
    return scores, stats, recency


def _shift_signal(rows: Iterable[Any]) -> dict[str, Any]:
    decoded = [decode_shift_topic(getattr(row, "topic", "")) for row in rows]
    if not decoded:
        return {"count": 0, "weakest_dimension": None, "weakest_factory": None, "dimension_scores": {}, "factory_scores": {}}

    dimension_keys = ("production_control", "prioritization", "production_judgement", "language")
    factory_keys = ("line", "quality", "material", "supplier", "load")
    dimension_scores = {
        key: round(sum(int(item.get(key, 0)) for item in decoded) / len(decoded)) for key in dimension_keys
    }
    factory_scores = {}
    for key in factory_keys:
        values = []
        for item in decoded:
            value = int((item.get("final_metrics") or {}).get(key, 0))
            values.append(100 - value if key == "load" else value)
        factory_scores[key] = round(sum(values) / len(values))
    return {
        "count": len(decoded),
        "weakest_dimension": min(dimension_scores, key=dimension_scores.get),
        "weakest_factory": min(factory_scores, key=factory_scores.get),
        "dimension_scores": dimension_scores,
        "factory_scores": factory_scores,
    }


def _adjusted_scores(base: dict[str, int], shift: dict[str, Any]) -> dict[str, int]:
    adjusted = dict(base)
    weakest_dimension = shift.get("weakest_dimension")
    if weakest_dimension:
        dimension_score = int((shift.get("dimension_scores") or {}).get(weakest_dimension, 100))
        penalty = max(4, round((100 - dimension_score) * 0.22))
        for skill in SHIFT_PRESSURE.get(str(weakest_dimension), ()):
            adjusted[skill] = max(0, adjusted[skill] - penalty)
    weakest_factory = shift.get("weakest_factory")
    if weakest_factory:
        factory_score = int((shift.get("factory_scores") or {}).get(weakest_factory, 100))
        penalty = max(3, round((100 - factory_score) * 0.16))
        for skill in FACTORY_PRESSURE.get(str(weakest_factory), ()):
            adjusted[skill] = max(0, adjusted[skill] - penalty)
    return adjusted


def _ordered_games(focus: str, stats: dict[str, dict[str, Any]], recency: dict[str, int]) -> list[str]:
    candidates = list(SKILLS[focus]["games"])

    def priority(game: str) -> tuple[int, int, int, str]:
        item = stats.get(game)
        if item is None:
            return (0, 0, 0, game)
        perfect_penalty = 1 if int(item.get("best", 0)) >= 100 else 0
        return (
            1 + perfect_penalty,
            int(item.get("recent_average", 100)),
            -int(recency.get(game, 9999)),
            game,
        )

    return sorted(candidates, key=priority)


def build_adaptive_plan(game_rows: Iterable[Any], shift_rows: Iterable[Any], language: str) -> dict[str, Any]:
    game_rows = list(game_rows)
    shift_rows = list(shift_rows)
    base_scores, stats, recency = _skill_scores(game_rows)
    shift = _shift_signal(shift_rows)
    adjusted = _adjusted_scores(base_scores, shift)
    if not game_rows and not shift_rows:
        focus = "vocabulary"
    else:
        focus = min(SKILLS, key=lambda key: (adjusted[key], base_scores[key], key))
    ordered = _ordered_games(focus, stats, recency)

    completed_games = len(game_rows)
    completed_shifts = int(shift.get("count", 0))
    confidence = "high" if completed_games >= 12 and completed_shifts >= 3 else "medium" if completed_games >= 4 or completed_shifts >= 1 else "starter"

    reasons = [f"Самый низкий устойчивый сигнал: {SKILLS[focus]['label']} — {adjusted[focus]}/100."]
    if shift.get("weakest_dimension"):
        reasons.append(f"Shift Review подтверждает точку роста: {shift['weakest_dimension']}.")
    if shift.get("weakest_factory"):
        reasons.append(f"Производственный сигнал для усиления: {shift['weakest_factory']}.")
    if completed_games < 4:
        reasons.append("Данных пока немного: план будет уточняться после следующих завершённых заданий.")

    first = ordered[0]
    second = ordered[1] if len(ordered) > 1 else ordered[0]
    plan = [
        {"step": 1, "kind": "game", "game_type": first, "title": GAME_TITLES[first], "purpose": f"Основная тренировка: {SKILLS[focus]['label']}."},
        {"step": 2, "kind": "game", "game_type": second, "title": GAME_TITLES[second], "purpose": "Закрепить тот же навык другой механикой, а не повторять один экран."},
        {"step": 3, "kind": "shift", "action": "shift_simulation", "title": "Shift Simulation", "purpose": "Проверить перенос навыка в связанную производственную смену."},
    ]
    return {
        "language": language,
        "focus_skill": focus,
        "focus_label": SKILLS[focus]["label"],
        "confidence": confidence,
        "skill_scores": base_scores,
        "adaptive_scores": adjusted,
        "shift_signal": shift,
        "reasons": reasons,
        "plan": plan,
        "source": {"completed_games": completed_games, "completed_shifts": completed_shifts},
        "policy": {"extra_xp": False, "max_answers_unchanged": True, "rotation": "weakest_skill_then_different_mechanic"},
    }


def build_adaptive_training_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    practice_result_model: Any,
    game_session_model: Any,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/adaptive-training/plan")
    def adaptive_training_plan(
        language: str = Query(default="chinese", pattern="^(chinese|english)$"),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        game_rows = list(
            db.scalars(
                select(game_session_model)
                .where(
                    game_session_model.user_id == user.id,
                    game_session_model.language == language,
                    game_session_model.status == "completed",
                )
                .order_by(game_session_model.completed_at.desc())
                .limit(120)
            ).all()
        )
        shift_rows = list(
            db.scalars(
                select(practice_result_model)
                .where(
                    practice_result_model.user_id == user.id,
                    practice_result_model.kind == SHIFT_KIND,
                    practice_result_model.language == language,
                )
                .order_by(practice_result_model.created_at.desc())
                .limit(20)
            ).all()
        )
        return build_adaptive_plan(game_rows, shift_rows, language)

    return router


__all__ = [
    "FACTORY_PRESSURE", "GAME_TITLES", "SHIFT_PRESSURE", "SKILLS",
    "build_adaptive_plan", "build_adaptive_training_router",
]
