from __future__ import annotations

from typing import Any, Callable, Mapping

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from mgc.config import TTS_MAX_CHARS


class PronunciationPayload(BaseModel):
    language: str
    text: str = Field(min_length=1, max_length=TTS_MAX_CHARS)
    rate: float = Field(default=0.9, ge=0.55, le=1.25)


PRONUNCIATION_HANDLER_NAMES = (
    "pronunciation_status",
    "pronunciation_audio_post",
)


def build_pronunciation_router(
    *,
    db_session: Callable[..., Any],
    current_user: Callable[..., Any],
    handlers: Mapping[str, Callable[..., Any]],
    legacy_get_enabled: bool,
    tts_max_chars: int = TTS_MAX_CHARS,
) -> APIRouter:
    """Build pronunciation/TTS HTTP routes over the existing offline TTS engine.

    v5.8.6 extracts HTTP ownership only. Synthesis, cache, circuit-breaker,
    feature-flag and pilot-quota semantics remain in the frozen legacy handlers
    and can move behind a dedicated TTS core in a later increment.
    """
    required = list(PRONUNCIATION_HANDLER_NAMES)
    if legacy_get_enabled:
        required.append("pronunciation_audio_legacy")
    missing = [name for name in required if not callable(handlers.get(name))]
    if missing:
        raise RuntimeError(f"pronunciation router handlers are incomplete: {missing}")

    pronunciation_status_handler = handlers["pronunciation_status"]
    pronunciation_audio_post_handler = handlers["pronunciation_audio_post"]
    pronunciation_audio_legacy_handler = handlers.get("pronunciation_audio_legacy")

    router = APIRouter()

    @router.get("/api/pronunciation/status")
    def pronunciation_status(user: Any = Depends(current_user)):
        return pronunciation_status_handler(user=user)

    @router.post("/api/pronunciation/audio")
    def pronunciation_audio_post(
        payload: PronunciationPayload,
        request: Request,
        user: Any = Depends(current_user),
        db: Session = Depends(db_session),
    ):
        return pronunciation_audio_post_handler(
            payload=payload,
            request=request,
            user=user,
            db=db,
        )

    if legacy_get_enabled:
        @router.get("/api/pronunciation/audio", deprecated=True)
        def pronunciation_audio_legacy(
            request: Request,
            language: str = Query(...),
            text_value: str = Query(
                ...,
                alias="text",
                min_length=1,
                max_length=tts_max_chars,
            ),
            rate: float = Query(default=0.9, ge=0.55, le=1.25),
            user: Any = Depends(current_user),
        ):
            assert pronunciation_audio_legacy_handler is not None
            return pronunciation_audio_legacy_handler(
                request=request,
                language=language,
                text_value=text_value,
                rate=rate,
                user=user,
            )

    return router


__all__ = [
    "PRONUNCIATION_HANDLER_NAMES",
    "PronunciationPayload",
    "build_pronunciation_router",
]
