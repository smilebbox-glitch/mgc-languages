from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session


SHIFT_KIND = "shift_simulation"
DIMENSIONS = (
    "production_control",
    "prioritization",
    "production_judgement",
    "language",
)
FACTORY_METRICS = ("line", "quality", "material", "supplier", "load")


class ShiftSimulationPayload(BaseModel):
    session_id: str = Field(min_length=6, max_length=120)
    language: str = Field(pattern="^(chinese|english)$")
    production_control: int = Field(ge=0, le=100)
    prioritization: int = Field(ge=0, le=100)
    production_judgement: int = Field(ge=0, le=100)
    language_score: int = Field(ge=0, le=100)
    total_score: int = Field(ge=0, le=100)
    weakest_dimension: str = Field(pattern="^(production_control|prioritization|production_judgement|language)$")
    factory_weakest: str = Field(pattern="^(line|quality|material|supplier|load)$")
    line: int = Field(ge=0, le=100)
    quality: int = Field(ge=0, le=100)
    material: int = Field(ge=0, le=100)
    supplier: int = Field(ge=0, le=100)
    load: int = Field(ge=0, le=100)
    duration_ms: int | None = Field(default=None, ge=1000, le=7_200_000)


_DIMENSION_CODES = {
    "production_control": "pc",
    "prioritization": "pr",
    "production_judgement": "pj",
    "language": "la",
}
_DIMENSION_FROM_CODE = {value: key for key, value in _DIMENSION_CODES.items()}
_FACTORY_CODES = {"line": "ln", "quality": "qu", "material": "ma", "supplier": "su", "load": "lo"}
_FACTORY_FROM_CODE = {value: key for key, value in _FACTORY_CODES.items()}


def encode_shift_topic(payload: ShiftSimulationPayload) -> str:
    values = [
        "v626",
        f"pc={payload.production_control}",
        f"pr={payload.prioritization}",
        f"pj={payload.production_judgement}",
        f"la={payload.language_score}",
        f"wd={_DIMENSION_CODES[payload.weakest_dimension]}",
        f"fw={_FACTORY_CODES[payload.factory_weakest]}",
        f"ln={payload.line}",
        f"qu={payload.quality}",
        f"ma={payload.material}",
        f"su={payload.supplier}",
        f"lo={payload.load}",
    ]
    if payload.duration_ms is not None:
        values.append(f"du={int(payload.duration_ms)}")
    encoded = "|".join(values)
    if len(encoded) > 160:
        raise RuntimeError("shift analytics payload exceeds PracticeResult.topic capacity")
    return encoded


def decode_shift_topic(topic: str) -> dict[str, Any]:
    parsed: dict[str, str] = {}
    for part in str(topic or "").split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key] = value

    def number(key: str) -> int:
        try:
            return max(0, min(100, int(parsed.get(key, "0"))))
        except (TypeError, ValueError):
            return 0

    duration_ms = None
    if "du" in parsed:
        try:
            duration_ms = max(1000, min(7_200_000, int(parsed["du"])))
        except (TypeError, ValueError):
            duration_ms = None

    return {
        "production_control": number("pc"),
        "prioritization": number("pr"),
        "production_judgement": number("pj"),
        "language": number("la"),
        "weakest_dimension": _DIMENSION_FROM_CODE.get(parsed.get("wd", ""), "production_control"),
        "factory_weakest": _FACTORY_FROM_CODE.get(parsed.get("fw", ""), "line"),
        "duration_ms": duration_ms,
        "final_metrics": {
            "line": number("ln"),
            "quality": number("qu"),
            "material": number("ma"),
            "supplier": number("su"),
            "load": number("lo"),
        },
    }


def summarize_shift_history(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "count": 0,
            "latest_total": None,
            "trend_delta": None,
            "averages": {key: None for key in DIMENSIONS},
            "weakest_dimension": None,
            "factory_weakest": None,
        }

    def avg(rows: list[dict[str, Any]], key: str) -> int:
        return round(sum(int(row.get(key, 0)) for row in rows) / max(1, len(rows)))

    averages = {key: avg(items, key) for key in DIMENSIONS}
    weakest_dimension = min(DIMENSIONS, key=lambda key: averages[key])

    factory_scores: dict[str, list[int]] = {key: [] for key in FACTORY_METRICS}
    for row in items:
        metrics = row.get("final_metrics") or {}
        for key in FACTORY_METRICS:
            value = int(metrics.get(key, 0))
            factory_scores[key].append(100 - value if key == "load" else value)
    factory_averages = {
        key: round(sum(values) / max(1, len(values))) for key, values in factory_scores.items()
    }
    factory_weakest = min(FACTORY_METRICS, key=lambda key: factory_averages[key])

    trend_delta = None
    if len(items) >= 4:
        recent = items[: min(3, len(items))]
        previous = items[len(recent): len(recent) * 2]
        if previous:
            recent_avg = round(sum(int(row.get("total_score", 0)) for row in recent) / len(recent))
            previous_avg = round(sum(int(row.get("total_score", 0)) for row in previous) / len(previous))
            trend_delta = recent_avg - previous_avg

    return {
        "count": len(items),
        "latest_total": int(items[0].get("total_score", 0)),
        "trend_delta": trend_delta,
        "averages": averages,
        "weakest_dimension": weakest_dimension,
        "factory_weakest": factory_weakest,
    }


def build_shift_analytics_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    practice_result_model: Any,
    storage_session_id: Callable[[int, str], str],
) -> APIRouter:
    router = APIRouter()

    def serialize(row: Any) -> dict[str, Any]:
        detail = decode_shift_topic(row.topic)
        return {
            "id": int(row.id),
            "learning_language": str(row.language),
            "total_score": int(row.score),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            **detail,
        }

    @router.post("/api/shift-simulations")
    def save_shift_simulation(
        payload: ShiftSimulationPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        scoped_session_id = storage_session_id(int(user.id), str(payload.session_id))
        existing = db.scalar(
            select(practice_result_model).where(
                practice_result_model.user_id == user.id,
                practice_result_model.session_id == scoped_session_id,
            )
        )
        if existing:
            return {"ok": True, "duplicate": True, "result": serialize(existing)}

        row = practice_result_model(
            user_id=user.id,
            session_id=scoped_session_id,
            kind=SHIFT_KIND,
            language=payload.language,
            topic=encode_shift_topic(payload),
            score=payload.total_score,
            total=100,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"ok": True, "duplicate": False, "result": serialize(row)}

    @router.get("/api/shift-simulations/history")
    def shift_simulation_history(
        limit: int = Query(default=12, ge=1, le=50),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        rows = list(
            db.scalars(
                select(practice_result_model)
                .where(
                    practice_result_model.user_id == user.id,
                    practice_result_model.kind == SHIFT_KIND,
                )
                .order_by(practice_result_model.created_at.desc())
                .limit(limit)
            ).all()
        )
        items = [serialize(row) for row in rows]
        return {"items": items, "summary": summarize_shift_history(items)}

    return router


__all__ = [
    "DIMENSIONS", "FACTORY_METRICS", "SHIFT_KIND", "ShiftSimulationPayload",
    "build_shift_analytics_router", "decode_shift_topic", "encode_shift_topic", "summarize_shift_history",
]
