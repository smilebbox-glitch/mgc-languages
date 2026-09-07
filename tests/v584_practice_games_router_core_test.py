from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.practice_games import (  # noqa: E402
    GameFinishPayload,
    PracticePayload,
    QuestionAttemptPayload,
    build_practice_games_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def dependency():
    yield object()


def handler(**kwargs):
    return {"ok": True}


router = build_practice_games_router(
    db_session=dependency,
    current_user=dependency,
    handlers={
        "save_practice_result": handler,
        "start_game": handler,
        "finish_game": handler,
        "question_attempt": handler,
    },
)

expected = {
    ("POST", "/api/practice/result"),
    ("POST", "/api/games/{game_type}/start"),
    ("POST", "/api/games/{session_id}/finish"),
    ("POST", "/api/learning/question-attempt"),
}
actual = set()
for route in router.routes:
    if not isinstance(route, APIRoute):
        continue
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path))
    assert route.endpoint.__module__ == "mgc.routers.practice_games"
assert actual == expected

valid = PracticePayload(
    session_id="v584-session",
    kind="quiz",
    language="chinese",
    topic="Сварка кузова",
    score=5,
    total=5,
)
assert valid.score == 5
try:
    PracticePayload(
        session_id="short",
        kind="unknown",
        language="chinese",
        score=5,
        total=5,
    )
    raise AssertionError("invalid practice payload accepted")
except ValidationError:
    pass

assert GameFinishPayload(answers=[1, 2]).answers == [1, 2]
attempt = QuestionAttemptPayload(
    question_id="q1",
    language="chinese",
    correct=True,
)
assert attempt.kind == "quiz"
assert attempt.response_ms == 0
try:
    QuestionAttemptPayload(
        question_id="q1",
        language="chinese",
        correct=False,
        response_ms=600001,
    )
    raise AssertionError("invalid response time accepted")
except ValidationError:
    pass

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.4 practice/game router builds independently with exact four-route contract")
