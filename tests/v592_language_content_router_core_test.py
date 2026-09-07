from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402
from mgc.routers.language_content import (  # noqa: E402
    LANGUAGE_CONTENT_HANDLER_NAMES,
    build_language_content_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def db_session():
    yield object()


def current_user():
    return object()


def make_handler(name: str):
    def handler(**kwargs):
        return {"handler": name, "keys": sorted(kwargs)}
    return handler


handlers = {name: make_handler(name) for name in LANGUAGE_CONTENT_HANDLER_NAMES}
router = build_language_content_router(
    db_session=db_session,
    current_user=current_user,
    handlers=handlers,
)
expected = {
    ("GET", "/api/language/{language}/summary", "language_summary"),
    ("GET", "/api/language/{language}/quiz", "language_quiz"),
    ("GET", "/api/language/{language}/situations", "situations"),
    ("GET", "/api/language/{language}/roleplays", "roleplays"),
    ("GET", "/api/language/{language}/mgc-scenarios", "mgc_scenarios"),
}
actual = set()
for route in router.routes:
    assert isinstance(route, APIRoute)
    methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
    assert len(methods) == 1
    actual.add((next(iter(methods)), route.path, route.name))
    assert route.endpoint.__module__ == "mgc.routers.language_content"
assert actual == expected

quiz = next(route for route in router.routes if route.path.endswith("/quiz"))
count_param = next(param for param in quiz.dependant.query_params if param.name == "count")
schema = count_param._type_adapter.json_schema()
assert schema["default"] == 10
assert schema["minimum"] == 5
assert schema["maximum"] == 30

assert len(LANGUAGE_CONTENT_HANDLER_NAMES) == 5
assert set(LANGUAGE_CONTENT_HANDLER_NAMES) == {item[2] for item in expected}
assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.9.2 dependency-light language content router preserves five routes and quiz bounds")
