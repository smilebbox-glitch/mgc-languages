from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
LEGACY_APP = (ROOT / "static/app.js").read_text(encoding="utf-8")
BRIDGE = (ROOT / "static/frontend/legacy_bridge.js").read_text(encoding="utf-8")
SESSION = (ROOT / "static/frontend/session_lifecycle.js").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

assert "document.addEventListener('DOMContentLoaded', boot);" in LEGACY_APP
for token in (
    "boot: requireFunction('boot', boot)",
    "bindStaticEvents: requireFunction('bindStaticEvents', bindStaticEvents)",
    "configureAuthUi: requireFunction('configureAuthUi', configureAuthUi)",
):
    assert token in BRIDGE, token

for token in (
    "document.removeEventListener('DOMContentLoaded', legacy.boot)",
    "document.addEventListener('DOMContentLoaded', bootstrap, {once: true})",
    "legacy.bindStaticEvents()",
    "apiClient.request('/api/meta')",
    "apiClient.request('/api/me')",
    "apiClient.request('/api/logout', {method: 'POST'})",
    "navigation.enterUserSession(user)",
    "navigation.leaveUserSession()",
    "event.stopImmediatePropagation()",
    "}, true)",
    "frontend.register('session-lifecycle'",
):
    assert token in SESSION, token

assert "'session-lifecycle'" in BOOT

assets = [
    "/frontend/navigation.js",
    "/frontend/session_lifecycle.js",
    "/auth_department.js",
    "/frontend/boot.js",
]
positions = [INDEX.index(asset) for asset in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/session_lifecycle.js') == 1

# The extraction intentionally leaves the historical bundle byte-for-byte untouched.
assert len(LEGACY_APP.encode("utf-8")) < 150_000

subprocess.run(
    ["node", "--check", str(ROOT / "static/frontend/session_lifecycle.js")],
    check=True,
    cwd=ROOT,
    capture_output=True,
    text=True,
)
subprocess.run(
    ["node", "--check", str(ROOT / "static/frontend/legacy_bridge.js")],
    check=True,
    cwd=ROOT,
    capture_output=True,
    text=True,
)

print("PASS: v6.0.1 modular session bootstrap/logout replaces legacy lifecycle without app.js rewrite")
