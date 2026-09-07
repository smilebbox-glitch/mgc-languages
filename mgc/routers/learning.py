from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class ProgressPayload(BaseModel):
    term_id: str
    status: str = Field(pattern="^(learning|known)$")


class CourseDayPayload(BaseModel):
    language: str
    day: int = Field(ge=1, le=30)
    score: int = Field(ge=0, le=5)
    total: int = Field(default=5, ge=5, le=5)


class SRSReviewPayload(BaseModel):
    language: str
    term_id: str = Field(min_length=1, max_length=80)
    quality: int = Field(ge=0, le=5)


class SpendPayload(BaseModel):
    reward_id: str = Field(min_length=2, max_length=80)
    language: str
    context: dict[str, Any] = Field(default_factory=dict)


class LearningSettingsPayload(BaseModel):
    show_pinyin: bool = True
    show_reading: bool = True
    server_audio_enabled: bool = True


LEARNING_HANDLER_NAMES = (
    "get_progress",
    "set_progress",
    "course30",
    "save_course_day",
    "review_queue",
    "review_result",
    "gamification_me",
    "gamification_levels",
    "gamification_rewards",
    "gamification_spend",
    "get_learning_preferences",
    "set_learning_preferences",
)


def build_learning_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build learning HTTP routes without importing the historical app module.

    v5.8.3 moves FastAPI route ownership while deliberately delegating the thin
    orchestration bodies to the frozen legacy handlers. Those handlers resolve
    XP/SRS and terminology helpers through module globals that are already bound
    to the extracted v5.7.7-v5.7.8 service layer before this router is built.
    """
    missing = [name for name in LEARNING_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"learning router handlers are incomplete: {missing}")

    get_progress_handler = handlers["get_progress"]
    set_progress_handler = handlers["set_progress"]
    course30_handler = handlers["course30"]
    save_course_day_handler = handlers["save_course_day"]
    review_queue_handler = handlers["review_queue"]
    review_result_handler = handlers["review_result"]
    gamification_me_handler = handlers["gamification_me"]
    gamification_levels_handler = handlers["gamification_levels"]
    gamification_rewards_handler = handlers["gamification_rewards"]
    gamification_spend_handler = handlers["gamification_spend"]
    get_learning_preferences_handler = handlers["get_learning_preferences"]
    set_learning_preferences_handler = handlers["set_learning_preferences"]

    router = APIRouter()

    @router.get("/api/language/{language}/progress")
    def get_progress(
        language: str,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return get_progress_handler(language=language, user=user, db=db)

    @router.post("/api/language/{language}/progress")
    def set_progress(
        language: str,
        payload: ProgressPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return set_progress_handler(language=language, payload=payload, user=user, db=db)

    @router.get("/api/language/{language}/course30")
    def course30(
        language: str,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return course30_handler(language=language, user=user, db=db)

    @router.post("/api/course-day/result")
    def save_course_day(
        payload: CourseDayPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return save_course_day_handler(payload=payload, user=user, db=db)

    @router.get("/api/review/queue")
    def review_queue(
        language: str = Query(default="chinese"),
        limit: int = Query(default=20, ge=1, le=100),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return review_queue_handler(language=language, limit=limit, user=user, db=db)

    @router.post("/api/review/result")
    def review_result(
        payload: SRSReviewPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return review_result_handler(payload=payload, user=user, db=db)

    @router.get("/api/gamification/me")
    def gamification_me(
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return gamification_me_handler(user=user, db=db)

    @router.get("/api/gamification/levels")
    def gamification_levels(user: Any = Depends(current_user)):
        return gamification_levels_handler(user=user)

    @router.get("/api/gamification/rewards")
    def gamification_rewards(
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return gamification_rewards_handler(user=user, db=db)

    @router.post("/api/gamification/spend")
    def gamification_spend(
        payload: SpendPayload,
        request: Request,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return gamification_spend_handler(
            payload=payload,
            request=request,
            user=user,
            db=db,
        )

    @router.get("/api/learning/preferences")
    def get_learning_preferences(
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return get_learning_preferences_handler(user=user, db=db)

    @router.put("/api/learning/preferences")
    def set_learning_preferences(
        payload: LearningSettingsPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return set_learning_preferences_handler(payload=payload, user=user, db=db)

    return router


__all__ = [
    "CourseDayPayload",
    "LEARNING_HANDLER_NAMES",
    "LearningSettingsPayload",
    "ProgressPayload",
    "SRSReviewPayload",
    "SpendPayload",
    "build_learning_router",
]
