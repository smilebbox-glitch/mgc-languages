from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
RUNTIME = (ROOT / "static/frontend/runtime.js").read_text(encoding="utf-8")
LEGACY_BRIDGE = (ROOT / "static/frontend/legacy_bridge.js").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
AUTH = (ROOT / "static/auth_department.js").read_text(encoding="utf-8")
LEGACY = (ROOT / "static/app.js").read_text(encoding="utf-8")

runtime_pos = INDEX.index('/frontend/runtime.js')
legacy_pos = INDEX.index('/app.js')
bridge_pos = INDEX.index('/frontend/legacy_bridge.js')
auth_pos = INDEX.index('/auth_department.js')
boot_pos = INDEX.index('/frontend/boot.js')
assert runtime_pos < legacy_pos < bridge_pos < auth_pos < boot_pos
for asset in (
    '/frontend/runtime.js', '/app.js', '/frontend/legacy_bridge.js',
    '/auth_department.js', '/frontend/boot.js'
):
    assert INDEX.count(asset) == 1, asset

for token in (
    "const modules = new Map()",
    "function register(name, api)",
    "Frontend module already registered",
    "Object.freeze(api || {})",
    "diagnostics.ready = true",
    "global.MGCFrontend = Object.freeze",
):
    assert token in RUNTIME, token

for token in (
    "frontend.register('legacy-app'",
    "getState: function () { return state; }",
    "setServiceStatus: requireFunction('setServiceStatus'",
):
    assert token in LEGACY_BRIDGE, token

for token in (
    "mgc:frontend-ready",
    "Frontend DOM contract missing",
    "frontend.markReady()",
    "requiredModules",
):
    assert token in BOOT, token

for dom_id in (
    "authView", "authForm", "username", "department", "password",
    "appView", "main", "sidebar", "logoutButton", "toast",
):
    assert f"'{dom_id}'" in BOOT

assert "window.MGCFrontend.register('auth-department'" in AUTH
assert "document.readyState === 'loading'" in AUTH
assert "event.stopImmediatePropagation()" in AUTH
assert "department: selectedDepartment" in AUTH

legacy_bytes = len(LEGACY.encode("utf-8"))
assert legacy_bytes < 150_000, legacy_bytes
assert "<script>" not in INDEX
assert "javascript:" not in INDEX.lower()

print("PASS: v5.9.9 frontend shell remains deterministic under v6.0.0 core extraction")
