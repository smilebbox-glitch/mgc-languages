from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

assert "mgc.legacy_app" not in sys.modules

from fastapi.routing import APIRoute  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.routers.learning import (  # noqa: E402
    CourseDayPayload,
    LEARNING_HANDLER_NAMES,
    ProgressPayload,
    SRSReviewPayload,
    build_learning_router,
)


def db_session():
    yield None


def current_user():
    return object()


def make_handler(name: str):
    def handler(**kwargs):
        return {"handler": name, "keys": sorted(kwargs)}
    handler.__name__ = name
    return handler


handlers = {name: make_handler(name) for name in LEARNING_HANDLER_NAMES}
router = build_learning_router(
    db_session=db_session,
    current_user=current_user,
    handlers=handlers,
)

expected = {
    ("GET", "/api/language/{language}/progress"),
    ("POST", "/api/language/{language}/progress"),
    ("GET", "/api/language/{language}/course30"),
    ("POST", "/api/course-day/result"),
    ("GET", "/api/review/queue"),
    ("POST", "/api/review/result"),
    ("GET", "/api/gamification/me"),
    ("GET", "/api/gamification/levels"),
    ("GET", "/api/gamification/rewards"),
    ("POST", "/api/gamification/spend"),
    ("GET", "/api/learning/preferences"),
    ("PUT", "/api/learning/preferences"),
}
actual = set()
names = set()
for route in router.routes:
    assert isinstance(route, APIRoute)
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path))
    names.add(route.name)
    assert route.endpoint.__module__ == "mgc.routers.learning"

assert actual == expected
assert names == set(LEARNING_HANDLER_NAMES)
assert len(actual) == 12

assert ProgressPayload(term_id="demo", status="known").status == "known"
try:
    ProgressPayload(term_id="demo", status="invalid")
except ValidationError:
    pass
else:
    raise AssertionError("ProgressPayload status contract drifted")

assert CourseDayPayload(language="chinese", day=30, score=5).total == 5
assert SRSReviewPayload(language="chinese", term_id="demo", quality=5).quality == 5
assert "mgc.legacy_app" not in sys.modules

print("OK: v5.8.3 dependency-light learning APIRouter owns the 12-route progress/course/SRS/gamification/preferences contract")
