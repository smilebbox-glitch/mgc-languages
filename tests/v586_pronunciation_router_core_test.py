from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from mgc.config import TTS_MAX_CHARS  # noqa: E402
from mgc.routers.pronunciation import (  # noqa: E402
    PronunciationPayload,
    build_pronunciation_router,
)

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules


def db_session():
    yield object()


def current_user():
    return object()


def pronunciation_status(**kwargs):
    return {"ok": True, "kind": "status"}


def pronunciation_audio_post(**kwargs):
    payload = kwargs["payload"]
    return {"ok": True, "kind": "post", "text": payload.text, "rate": payload.rate}


def pronunciation_audio_legacy(**kwargs):
    return {"ok": True, "kind": "legacy", "text": kwargs["text_value"], "rate": kwargs["rate"]}


handlers = {
    "pronunciation_status": pronunciation_status,
    "pronunciation_audio_post": pronunciation_audio_post,
    "pronunciation_audio_legacy": pronunciation_audio_legacy,
}


def route_contract(router):
    result = set()
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = (route.methods or set()) - {"HEAD", "OPTIONS"}
        assert len(methods) == 1
        result.add((next(iter(methods)), route.path))
        assert route.endpoint.__module__ == "mgc.routers.pronunciation"
    return result


without_legacy = build_pronunciation_router(
    db_session=db_session,
    current_user=current_user,
    handlers=handlers,
    legacy_get_enabled=False,
    tts_max_chars=TTS_MAX_CHARS,
)
assert route_contract(without_legacy) == {
    ("GET", "/api/pronunciation/status"),
    ("POST", "/api/pronunciation/audio"),
}

with_legacy = build_pronunciation_router(
    db_session=db_session,
    current_user=current_user,
    handlers=handlers,
    legacy_get_enabled=True,
    tts_max_chars=TTS_MAX_CHARS,
)
assert route_contract(with_legacy) == {
    ("GET", "/api/pronunciation/status"),
    ("POST", "/api/pronunciation/audio"),
    ("GET", "/api/pronunciation/audio"),
}
legacy_route = next(
    route for route in with_legacy.routes
    if isinstance(route, APIRoute)
    and route.path == "/api/pronunciation/audio"
    and "GET" in (route.methods or set())
)
assert legacy_route.deprecated is True

valid = PronunciationPayload(language="chinese", text="你好", rate=0.9)
assert valid.text == "你好"
assert valid.rate == 0.9
for bad_rate in (0.54, 1.26):
    try:
        PronunciationPayload(language="english", text="hello", rate=bad_rate)
        raise AssertionError("invalid pronunciation rate accepted")
    except ValidationError:
        pass
try:
    PronunciationPayload(language="english", text="x" * (TTS_MAX_CHARS + 1), rate=0.9)
    raise AssertionError("oversized pronunciation text accepted")
except ValidationError:
    pass

app = FastAPI()
app.include_router(with_legacy)
client = TestClient(app)
assert client.get("/api/pronunciation/status").status_code == 200
post = client.post(
    "/api/pronunciation/audio",
    json={"language": "english", "text": "hello", "rate": 1.0},
)
assert post.status_code == 200, post.text
assert post.json()["kind"] == "post"
legacy = client.get(
    "/api/pronunciation/audio",
    params={"language": "english", "text": "hello", "rate": 1.0},
)
assert legacy.status_code == 200, legacy.text
assert legacy.json()["kind"] == "legacy"
assert client.get(
    "/api/pronunciation/audio",
    params={"language": "english", "text": "x" * (TTS_MAX_CHARS + 1)},
).status_code == 422
openapi = app.openapi()
assert openapi["paths"]["/api/pronunciation/audio"]["get"]["deprecated"] is True

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.6 pronunciation router builds independently with conditional legacy GET and exact validation")
