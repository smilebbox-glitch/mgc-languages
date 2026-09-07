from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "8"))
STARTUP_TIMEOUT = float(os.getenv("SMOKE_STARTUP_TIMEOUT_SECONDS", "45"))


def get(path: str):
    req = urllib.request.Request(BASE_URL + path, headers={"User-Agent": "mgc-languages-runtime-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, content_type, body


def wait_until_ready():
    deadline = time.monotonic() + STARTUP_TIMEOUT
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, content_type, body = get("/health/ready")
            if status == 200:
                payload = json.loads(body.decode("utf-8"))
                if payload.get("status") == "ready":
                    return payload
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(1)
    raise AssertionError(f"service did not become ready at {BASE_URL}: {last_error}")


ready = wait_until_ready()
assert ready["status"] == "ready"
assert isinstance(ready.get("checks"), dict) and ready["checks"], ready

status, content_type, body = get("/health/live")
assert status == 200
assert "application/json" in content_type.lower(), content_type
live = json.loads(body.decode("utf-8"))
assert live.get("status") == "ok", live
assert live.get("service") == "mgc-languages", live
assert live.get("version") == "5.7.1", live

status, content_type, body = get("/api/meta")
assert status == 200
assert "application/json" in content_type.lower(), content_type
meta = json.loads(body.decode("utf-8"))
assert meta.get("title") == "MGC Languages", meta
assert meta.get("version") == "5.7.1", meta
assert meta.get("chinese_learning_standard") == "Путунхуа (普通话) — стандартный китайский", meta
assert {row.get("id") for row in meta.get("languages", [])} == {"english", "chinese"}, meta

for path, expected_type, minimum_size in (
    ("/", "text/html", 1000),
    ("/app.js", "javascript", 50000),
    ("/styles.css", "text/css", 10000),
):
    status, content_type, body = get(path)
    assert status == 200, (path, status)
    assert expected_type in content_type.lower(), (path, content_type)
    assert len(body) >= minimum_size, (path, len(body), minimum_size)

print(f"OK: runtime smoke passed for {BASE_URL} — health, readiness, meta, UI and static assets")
