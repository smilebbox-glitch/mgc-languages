from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
RUNTIME = (ROOT / "static/frontend/runtime.js").read_text(encoding="utf-8")
BRIDGE = (ROOT / "static/frontend/legacy_bridge.js").read_text(encoding="utf-8")
STATUS = (ROOT / "static/frontend/service_status.js").read_text(encoding="utf-8")
API = (ROOT / "static/frontend/api_client.js").read_text(encoding="utf-8")
STATE = (ROOT / "static/frontend/app_state.js").read_text(encoding="utf-8")
NAV = (ROOT / "static/frontend/navigation.js").read_text(encoding="utf-8")
AUTH = (ROOT / "static/auth_department.js").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

assets = [
    "/frontend/runtime.js",
    "/app.js",
    "/frontend/legacy_bridge.js",
    "/frontend/service_status.js",
    "/frontend/api_client.js",
    "/frontend/app_state.js",
    "/frontend/navigation.js",
    "/auth_department.js",
    "/frontend/boot.js",
]
positions = [INDEX.index(asset) for asset in assets]
assert positions == sorted(positions), positions
assert all(INDEX.count(asset) == 1 for asset in assets)

assert "version: '6.0.0'" in RUNTIME
assert "frontend.register('legacy-app'" in BRIDGE
assert "frontend.register('service-status'" in STATUS
assert "frontend.register('api-client'" in API
assert "frontend.register('app-state'" in STATE
assert "frontend.register('navigation'" in NAV

for token in (
    "credentials: 'same-origin'",
    "X-CSRF-Token",
    "response.status === 401",
    "Требуется повторный вход",
    "database_unavailable",
    "service-status",
):
    assert token in API, token

for token in (
    "mgc:state-change",
    "function patch(values)",
    "current()[key] = value",
):
    assert token in STATE, token

for token in (
    "enterUserSession",
    "leaveUserSession",
    "preferred_language",
    "legacy().setView('home')",
):
    assert token in NAV, token

for dependency in ("api-client", "app-state", "navigation"):
    assert dependency in AUTH
assert "legacy-app" not in AUTH
assert "legacy.getState" not in AUTH
assert "const request =" not in AUTH
assert "await apiClient.request" in AUTH
assert "await navigation.enterUserSession(result.user)" in AUTH

for required in (
    "'legacy-app'",
    "'service-status'",
    "'api-client'",
    "'app-state'",
    "'navigation'",
    "'auth-department'",
):
    assert required in BOOT

for script in (
    "runtime.js",
    "legacy_bridge.js",
    "service_status.js",
    "api_client.js",
    "app_state.js",
    "navigation.js",
    "boot.js",
):
    subprocess.run(
        ["node", "--check", str(ROOT / "static/frontend" / script)],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
subprocess.run(
    ["node", "--check", str(ROOT / "static/auth_department.js")],
    check=True,
    cwd=ROOT,
    capture_output=True,
    text=True,
)

print("PASS: v6.0.0 modular API/state/navigation core owns auth dependencies without app.js rewrite")
