from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402
import mgc.tts_core as tts_module  # noqa: E402
from mgc.tts_core import TTSCoreConfig, build_tts_core  # noqa: E402

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules

cache_dir = Path(tempfile.mkdtemp(prefix="mgc-v587-tts-core-"))
events = []
rate_calls = []
warnings = []
subprocess_calls = []


def validate_language(language: str) -> str:
    if language not in {"english", "chinese"}:
        raise HTTPException(400, "Неизвестный язык")
    return language


def rate_limit(request, bucket: str, limit: int, window_seconds: int) -> None:
    rate_calls.append((bucket, limit, window_seconds))


def operational_event(event_type: str, **kwargs) -> None:
    events.append((event_type, kwargs))


class Logger:
    def warning(self, value):
        warnings.append(value)


class FakeResult:
    returncode = 0
    stdout = b"RIFF" + b"\x00" * 700
    stderr = b""


def fake_run(args, **kwargs):
    subprocess_calls.append((args, kwargs))
    return FakeResult()


config = TTSCoreConfig(
    enabled=True,
    binary="/fake/espeak-ng",
    voice_chinese="zh",
    voice_english="en-us",
    timeout_seconds=3,
    concurrency=2,
    failure_threshold=2,
    circuit_cooldown_seconds=30,
    health_ttl_seconds=10,
    disk_cache_enabled=True,
    cache_dir=cache_dir,
    disk_cache_max_mb=8,
    disk_cache_ttl_hours=1,
    cache_persistence="ephemeral",
)

original_run = tts_module.subprocess.run
tts_module.subprocess.run = fake_run
try:
    bindings = build_tts_core(
        config=config,
        validate_language=validate_language,
        rate_limit=rate_limit,
        operational_event=operational_event,
        logger=Logger(),
    )

    for function in (
        bindings.cache_path,
        bindings.cache_read,
        bindings.prune_cache,
        bindings.cache_write,
        bindings.circuit_open,
        bindings.mark_success,
        bindings.mark_failure,
        bindings.synthesize_wav,
        bindings.health,
        bindings.pronunciation_response,
    ):
        assert function.__module__ == "mgc.tts_core"

    expected_digest = hashlib.sha256(
        "v5.3.2|english|90|cache me".encode("utf-8")
    ).hexdigest()
    assert bindings.cache_path("english", "cache me", 90) == cache_dir / f"{expected_digest}.wav"

    valid_wav = b"RIFF" + b"a" * 700
    bindings.cache_write("english", "cache me", 90, valid_wav)
    assert bindings.runtime["disk_cache_writes"] == 1
    assert bindings.cache_read("english", "cache me", 90) == valid_wav
    assert bindings.runtime["disk_cache_hits"] == 1

    invalid_path = bindings.cache_path("english", "invalid", 90)
    bindings.cache_write("english", "invalid", 90, b"not-wav")
    assert not invalid_path.exists()

    fresh = bindings.synthesize_wav("english", "fresh synthesis", 100)
    assert fresh.startswith(b"RIFF") and len(fresh) > 512
    assert subprocess_calls
    assert subprocess_calls[-1][0] == [
        "/fake/espeak-ng", "-v", "en-us", "-s", "175", "--stdout"
    ]
    assert bindings.runtime["success_total"] == 1
    assert bindings.synthesize_wav.cache_info().maxsize == 256

    before_calls = len(subprocess_calls)
    bindings.synthesize_wav.cache_clear()
    cached = bindings.synthesize_wav("english", "fresh synthesis", 100)
    assert cached == fresh
    assert len(subprocess_calls) == before_calls
    assert bindings.runtime["disk_cache_hits"] >= 2

    bindings.mark_failure()
    assert not bindings.circuit_open()
    bindings.mark_failure()
    assert bindings.circuit_open()
    assert bindings.runtime["failure_total"] == 2
    bindings.mark_success()
    assert not bindings.circuit_open()
    assert bindings.runtime["consecutive_failures"] == 0

    health = bindings.health(force=True)
    assert health["server_available"] is True
    assert health["offline"] is True
    assert health["engine"] == "espeak-ng"
    assert health["voices"] == {"chinese": "zh", "english": "en-us"}
    assert health["language_checks"] == {"chinese": True, "english": True}
    assert health["timeout_seconds"] == 3
    assert health["concurrency"] == 2
    assert health["disk_cache_enabled"] is True
    assert health["cache_persistence"] == "ephemeral"
    assert health["cache_writable"] is True
    assert set(health["runtime"]) == {
        "success_total", "failure_total", "disk_cache_hits", "disk_cache_writes",
        "consecutive_failures", "circuit_open_until",
    }

    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/pronunciation/audio",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "scheme": "http",
    })
    response = bindings.pronunciation_response(request, "english", "hello core", 1.0)
    assert response.media_type == "audio/wav"
    assert response.headers["content-disposition"] == "inline; filename=pronunciation.wav"
    assert response.headers["x-tts-engine"] == "espeak-ng"
    assert response.headers["x-tts-voice"] == "en-us"
    assert response.headers["cache-control"] == "no-store"
    assert rate_calls[-1] == ("tts", 90, 60)
finally:
    tts_module.subprocess.run = original_run

fallback_events = []
fallback = build_tts_core(
    config=TTSCoreConfig(
        enabled=False,
        binary="",
        voice_chinese="zh",
        voice_english="en-us",
        timeout_seconds=3,
        concurrency=1,
        failure_threshold=2,
        circuit_cooldown_seconds=30,
        health_ttl_seconds=10,
        disk_cache_enabled=False,
        cache_dir=cache_dir / "disabled",
        disk_cache_max_mb=8,
        disk_cache_ttl_hours=1,
        cache_persistence="ephemeral",
    ),
    validate_language=validate_language,
    rate_limit=lambda *args: None,
    operational_event=lambda event_type, **kwargs: fallback_events.append((event_type, kwargs)),
    logger=Logger(),
)
request = Request({
    "type": "http",
    "method": "POST",
    "path": "/api/pronunciation/audio",
    "headers": [],
    "query_string": b"",
    "client": ("127.0.0.1", 1234),
    "server": ("testserver", 80),
    "scheme": "http",
})
try:
    fallback.pronunciation_response(request, "chinese", "你好", 0.9)
    raise AssertionError("disabled TTS unexpectedly synthesized audio")
except HTTPException as exc:
    assert exc.status_code == 503
    assert "browser fallback" in str(exc.detail)
assert fallback_events and fallback_events[-1][0] == "tts.fallback"
assert fallback.health(force=True)["cache_writable"] is True

assert "mgc.legacy_app" not in sys.modules
assert "app" not in sys.modules
print("OK: v5.8.7 isolated TTS core preserves cache, LRU, circuit, health, synthesis and fallback contracts")
