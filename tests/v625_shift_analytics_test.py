from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mgc.routers.shift_analytics import (  # noqa: E402
    ShiftSimulationPayload,
    decode_shift_topic,
    encode_shift_topic,
    summarize_shift_history,
)

ROUTER = (ROOT / "mgc/routers/shift_analytics.py").read_text(encoding="utf-8")
BRIDGE = (ROOT / "mgc_core/shift_analytics_router_bridge.py").read_text(encoding="utf-8")
RUNTIME = (ROOT / "mgc_core/runtime.py").read_text(encoding="utf-8")
ASGI = (ROOT / "asgi.py").read_text(encoding="utf-8")
FRONTEND = (ROOT / "static/frontend/shift_analytics_v625.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/shift_analytics_v625.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

payload = ShiftSimulationPayload(
    session_id="shift-v625-regression", language="chinese", production_control=82,
    prioritization=76, production_judgement=91, language_score=68, total_score=81,
    weakest_dimension="language", factory_weakest="supplier", line=84, quality=79,
    material=73, supplier=61, load=42,
)
encoded = encode_shift_topic(payload)
assert len(encoded) <= 160
parsed = decode_shift_topic(encoded)
assert parsed["production_control"] == 82
assert parsed["prioritization"] == 76
assert parsed["production_judgement"] == 91
assert parsed["language"] == 68
assert parsed["weakest_dimension"] == "language"
assert parsed["factory_weakest"] == "supplier"
assert parsed["final_metrics"]["load"] == 42

history = [
    {"total_score": 81, "production_control": 82, "prioritization": 76, "production_judgement": 91, "language": 68,
     "final_metrics": {"line": 84, "quality": 79, "material": 73, "supplier": 61, "load": 42}},
    {"total_score": 77, "production_control": 80, "prioritization": 72, "production_judgement": 86, "language": 66,
     "final_metrics": {"line": 82, "quality": 74, "material": 70, "supplier": 58, "load": 45}},
    {"total_score": 74, "production_control": 78, "prioritization": 69, "production_judgement": 83, "language": 64,
     "final_metrics": {"line": 79, "quality": 72, "material": 68, "supplier": 55, "load": 48}},
    {"total_score": 70, "production_control": 75, "prioritization": 65, "production_judgement": 80, "language": 60,
     "final_metrics": {"line": 76, "quality": 70, "material": 65, "supplier": 52, "load": 51}},
]
summary = summarize_shift_history(history)
assert summary["count"] == 4
assert summary["latest_total"] == 81
assert summary["weakest_dimension"] == "language"
assert summary["factory_weakest"] == "load"
assert summary["trend_delta"] is not None

for marker in [
    'SHIFT_KIND = "shift_simulation"', '@router.post("/api/shift-simulations")',
    '@router.get("/api/shift-simulations/history")', "practice_result_model.user_id == user.id",
    "storage_session_id(int(user.id)", "kind=SHIFT_KIND", "topic=encode_shift_topic(payload)",
    '"learning_language": str(row.language)',
]:
    assert marker in ROUTER, marker
for forbidden in ["XPEvent", "spendable_xp", "awarded_xp", "/api/games/"]:
    assert forbidden not in ROUTER, forbidden

for marker in [
    '("POST", "/api/shift-simulations")', '("GET", "/api/shift-simulations/history")',
    "application.router.routes.insert(insert_at, route)", "practice_storage_session_id", "user_scoped_storage",
]:
    assert marker in BRIDGE, marker
assert "bind_shift_analytics_router(module, application)" in RUNTIME
assert "SHIFT_ANALYTICS_ROUTER_BINDING_REPORT" in RUNTIME
assert "SHIFT_ANALYTICS_ROUTER_BINDING_REPORT" in ASGI

for marker in [
    'frontend.register("shift-analytics-v625"', 'const API_ROOT = "/api/shift-simulations"',
    'const PENDING_KEY = "mgc.v625.shift.pending"', 'summary.dataset.v625Captured = "1"',
    "enqueue(payload)", "flushPending()", 'API_ROOT + "/history?limit=20"',
    "PERSONAL SHIFT ANALYTICS · v6.0.25", "ПОВТОРЯЮЩАЯСЯ ТОЧКА РОСТА",
    "Тренировать в новой смене", "История сохраняется под вашим аккаунтом в PostgreSQL",
]:
    assert marker in FRONTEND, marker
for forbidden in ["awarded_xp", "spendable_xp", "/api/games/"]:
    assert forbidden not in FRONTEND, forbidden

assert "/shift_analytics_v625.css" in INDEX
assert "/frontend/shift_analytics_v625.js" in INDEX
assert INDEX.index("shift_simulation_v624.js") < INDEX.index("shift_analytics_v625.js") < INDEX.index("frontend/boot.js")
assert "'shift-analytics-v625'" in BOOT
assert "pilotCandidate: 'v6.0." in BOOT
assert ".v625-analytics-panel" in CSS
assert ".v625-history-row" in CSS

subprocess.run(["node", "--check", str(ROOT / "static/frontend/shift_analytics_v625.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.25 persists account-scoped Shift Simulation history, trends and personalized next-training guidance without adding XP")
