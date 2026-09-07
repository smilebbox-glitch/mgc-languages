from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_capacity(**overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "WEB_CONCURRENCY": "2",
            "DB_POOL_SIZE": "5",
            "DB_MAX_OVERFLOW": "5",
            "POSTGRES_MAX_CONNECTIONS": "120",
            "DB_CONNECTION_RESERVE": "20",
            "CAPACITY_EXPECTED_AUX_CONNECTIONS": "8",
        }
    )
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "scripts/capacity_preflight.py"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )


safe = run_capacity()
assert safe.returncode == 0, safe.stderr
report = json.loads(safe.stdout.splitlines()[0])
assert report["workers"] == 2
assert report["per_worker_peak_connections"] == 10
assert report["application_peak_connections"] == 20
assert report["usable_application_connections"] == 92
assert report["headroom_after_application_peak"] == 72
assert report["ok"] is True

unsafe = run_capacity(WEB_CONCURRENCY="8", DB_POOL_SIZE="10", DB_MAX_OVERFLOW="10")
assert unsafe.returncode == 2
unsafe_report = json.loads(unsafe.stdout.splitlines()[0])
assert unsafe_report["application_peak_connections"] == 160
assert unsafe_report["ok"] is False
assert "connection budget" in unsafe.stderr

invalid = run_capacity(WEB_CONCURRENCY="abc")
assert invalid.returncode != 0
assert "WEB_CONCURRENCY must be an integer" in invalid.stderr

entrypoint = (ROOT / "scripts/entrypoint.sh").read_text(encoding="utf-8")
assert "python scripts/capacity_preflight.py" in entrypoint
assert "uvicorn asgi:app" in entrypoint
assert '--limit-concurrency "$limit_concurrency"' in entrypoint
assert '--backlog "$backlog"' in entrypoint
assert '--timeout-keep-alive "$keep_alive"' in entrypoint

compose = (ROOT / "docker-compose.lan.yml").read_text(encoding="utf-8")
assert "max_connections=${POSTGRES_MAX_CONNECTIONS:-120}" in compose
assert "POSTGRES_MAX_CONNECTIONS: ${POSTGRES_MAX_CONNECTIONS:-120}" in compose
assert "DB_CONNECTION_RESERVE: ${DB_CONNECTION_RESERVE:-20}" in compose
assert "CAPACITY_EXPECTED_AUX_CONNECTIONS: ${CAPACITY_EXPECTED_AUX_CONNECTIONS:-8}" in compose
assert "UVICORN_LIMIT_CONCURRENCY: ${UVICORN_LIMIT_CONCURRENCY:-200}" in compose
assert "DB_POOL_TIMEOUT: ${DB_POOL_TIMEOUT:-10}" in compose

# Only nginx may publish a host port in the LAN profile.
assert compose.count("ports:") == 1
assert '${MGC_BIND_ADDRESS:-0.0.0.0}:${MGC_PORT:-8080}:8080' in compose

nginx = (ROOT / "deploy/nginx/default.conf").read_text(encoding="utf-8")
assert "upstream mgc_app" in nginx
assert "keepalive 64" in nginx
assert 'proxy_set_header Connection "";' in nginx
assert "proxy_connect_timeout 3s" in nginx

smoke = (ROOT / "scripts/multi_user_smoke.py").read_text(encoding="utf-8")
for name in ("smoke", "office", "burst"):
    assert f'"{name}"' in smoke
assert '"p99"' in smoke
assert "min_success_rate" in smoke

print("PASS: v5.9.4 capacity topology and overload guards")
