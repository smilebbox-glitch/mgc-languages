from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(tempfile.gettempdir()) / "mgc_languages_v573_entrypoint.db"
try:
    DB.unlink()
except FileNotFoundError:
    pass

os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "AUTO_CREATE_SCHEMA": "true",
    "APP_ENV": "development",
    "AUTH_MODE": "local",
    "REGISTRATION_ENABLED": "true",
    "TRUSTED_HOSTS": "testserver,localhost,127.0.0.1",
    "OIDC_STATE_SECRET": "v573-entrypoint-contract-secret-000001",
    "TTS_ENABLED": "false",
})
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from mgc_core.contracts import CRITICAL_ROUTE_CONTRACT, route_inventory  # noqa: E402
import asgi  # noqa: E402

legacy = importlib.import_module("app")
assert asgi.app is legacy.app
assert asgi.CONTRACT_REPORT.ok
inventory = set(route_inventory(asgi.app))
assert CRITICAL_ROUTE_CONTRACT.issubset(inventory)
assert asgi.CONTRACT_REPORT.route_count == asgi.CONTRACT_REPORT.unique_route_count

client = TestClient(asgi.app)
health = client.get("/health")
assert health.status_code == 200, health.text
assert health.json()["service"] == "mgc-languages"
meta = client.get("/api/meta")
assert meta.status_code == 200, meta.text
assert meta.json()["title"] == "MGC Languages"

dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
assert '"asgi:app"' in dockerfile
assert '"app:app"' not in dockerfile

print("OK: v5.7.3 modular ASGI entrypoint preserves the legacy FastAPI object and critical route contract")
