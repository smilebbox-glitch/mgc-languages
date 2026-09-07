from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session


LANGUAGE_CONTENT_HANDLER_NAMES = (
    "language_summary",
    "language_quiz",
    "situations",
    "roleplays",
    "mgc_scenarios",
)


def build_language_content_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build authenticated language summary, quiz and scenario content routes."""
    missing = [name for name in LANGUAGE_CONTENT_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"language content router handlers are incomplete: {missing}")

    router = APIRouter()

    @router.get("/api/language/{language}/summary")
    def language_summary(
        language: str,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return handlers["language_summary"](language=language, user=user, db=db)

    @router.get("/api/language/{language}/quiz")
    def language_quiz(
        language: str,
        topic: str | None = None,
        level: str | None = None,
        count: int = Query(default=10, ge=5, le=30),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return handlers["language_quiz"](
            language=language,
            topic=topic,
            level=level,
            count=count,
            user=user,
            db=db,
        )

    @router.get("/api/language/{language}/situations")
    def situations(language: str, user: Any = Depends(current_user)):
        return handlers["situations"](language=language, user=user)

    @router.get("/api/language/{language}/roleplays")
    def roleplays(language: str, user: Any = Depends(current_user)):
        return handlers["roleplays"](language=language, user=user)

    @router.get("/api/language/{language}/mgc-scenarios")
    def mgc_scenarios(language: str, user: Any = Depends(current_user)):
        return handlers["mgc_scenarios"](language=language, user=user)

    return router


__all__ = ["LANGUAGE_CONTENT_HANDLER_NAMES", "build_language_content_router"]
