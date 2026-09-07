from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class PracticePayload(BaseModel):
    session_id: str = Field(min_length=6, max_length=120)
    kind: str = Field(pattern="^(quiz|scenario|pair|course_day|exam|tone_lab)$")
    language: str
    topic: str = Field(default="", max_length=160)
    score: int = Field(ge=0, le=100)
    total: int = Field(ge=1, le=100)


class GameFinishPayload(BaseModel):
    answers: list[Any] = Field(default_factory=list, max_length=50)


class QuestionAttemptPayload(BaseModel):
    session_id: str = Field(default="", max_length=120)
    question_id: str = Field(min_length=1, max_length=160)
    term_id: str = Field(default="", max_length=80)
    language: str
    topic: str = Field(default="", max_length=160)
    kind: str = Field(default="quiz", max_length=50)
    correct: bool
    response_ms: int = Field(default=0, ge=0, le=600000)
    selected: str = Field(default="", max_length=1000)


PRACTICE_GAME_HANDLER_NAMES = (
    "save_practice_result",
    "start_game",
    "finish_game",
    "question_attempt",
)


def build_practice_games_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    handlers: Mapping[str, Callable[..., Any]],
) -> APIRouter:
    """Build practice/game HTTP routes over the extracted v5.7.9 workflows."""
    missing = [name for name in PRACTICE_GAME_HANDLER_NAMES if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"practice/game router handlers are incomplete: {missing}")

    save_practice_result_handler = handlers["save_practice_result"]
    start_game_handler = handlers["start_game"]
    finish_game_handler = handlers["finish_game"]
    question_attempt_handler = handlers["question_attempt"]

    router = APIRouter()

    @router.post("/api/practice/result")
    def save_practice_result(
        payload: PracticePayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return save_practice_result_handler(payload=payload, user=user, db=db)

    @router.post("/api/games/{game_type}/start")
    def start_game(
        game_type: str,
        language: str = Query(default="chinese"),
        topic: str = Query(default=""),
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return start_game_handler(
            game_type=game_type,
            language=language,
            topic=topic,
            user=user,
            db=db,
        )

    @router.post("/api/games/{session_id}/finish")
    def finish_game(
        session_id: str,
        payload: GameFinishPayload,
        request: Request,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return finish_game_handler(
            session_id=session_id,
            payload=payload,
            request=request,
            user=user,
            db=db,
        )

    @router.post("/api/learning/question-attempt")
    def question_attempt(
        payload: QuestionAttemptPayload,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return question_attempt_handler(payload=payload, user=user, db=db)

    return router


__all__ = [
    "GameFinishPayload",
    "PRACTICE_GAME_HANDLER_NAMES",
    "PracticePayload",
    "QuestionAttemptPayload",
    "build_practice_games_router",
]
