from __future__ import annotations

import hashlib
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session


class _ScopedPracticePayload:
    def __init__(self, original: Any, session_id: str) -> None:
        self._original = original
        self.session_id = session_id

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


def practice_storage_session_id(user_id: int, raw_session_id: str) -> str:
    digest = hashlib.sha256(raw_session_id.encode("utf-8")).hexdigest()
    return f"u{int(user_id)}:{digest}"


def build_user_scoped_practice_save(
    *,
    original_save: Callable[..., dict[str, Any]],
    practice_result_model: Any,
    gamification_view: Callable[[Session, int], dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    """Scope practice idempotency by user without changing the DB schema.

    Historical rows stored the raw client session_id under a globally unique column.
    New rows store a deterministic user-scoped hash, so two users may safely submit
    the same client session_id while old rows for the same user remain idempotent.
    """

    def save_practice_result(payload: Any, user: Any, db: Session) -> dict[str, Any]:
        raw_session_id = str(payload.session_id)
        legacy = db.scalar(
            select(practice_result_model).where(
                practice_result_model.user_id == user.id,
                practice_result_model.session_id == raw_session_id,
            )
        )
        if legacy:
            return {
                "ok": True,
                "duplicate": True,
                "profile": gamification_view(db, user.id),
            }

        scoped_session_id = practice_storage_session_id(user.id, raw_session_id)
        scoped_payload = _ScopedPracticePayload(payload, scoped_session_id)
        return original_save(scoped_payload, user, db)

    save_practice_result.__name__ = "save_practice_result"
    save_practice_result.__qualname__ = "save_practice_result"
    return save_practice_result


__all__ = [
    "build_user_scoped_practice_save",
    "practice_storage_session_id",
]
