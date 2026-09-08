from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mgc.routers.adaptive_training import SKILLS, build_adaptive_plan  # noqa: E402

ROUTER = (ROOT / "mgc/routers/adaptive_training.py").read_text(encoding="utf-8")
BRIDGE = (ROOT / "mgc_core/adaptive_training_router_bridge.py").read_text(encoding="utf-8")
RUNTIME = (ROOT / "mgc_core/runtime.py").read_text(encoding="utf-8")
ASGI = (ROOT / "asgi.py").read_text(encoding="utf-8")
CONTRACTS = (ROOT / "mgc_core/contracts.py").read_text(encoding="utf-8")
FRONTEND = (ROOT / "static/frontend/adaptive_training_v627.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/adaptive_training_v627.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# Seven stable automotive learning competencies remain aligned with Arcade Mastery.
assert set(SKILLS) == {
    "vocabulary", "listening", "production", "quality", "logistics", "engineering", "communication"
}
assert "quality_gate" in SKILLS["quality"]["games"]
assert "dialogue_choice" in SKILLS["communication"]["games"]
assert "bom_builder" in SKILLS["engineering"]["games"]

# A weak quality history plus weak production judgement / quality factory state must drive a quality-focused loop.
games = [
    SimpleNamespace(game_type="quality_gate", score=2, total=5),
    SimpleNamespace(game_type="defect_detective", score=2, total=5),
]
shifts = [SimpleNamespace(topic="v626|pc=82|pr=76|pj=35|la=91|wd=pj|fw=qu|ln=78|qu=40|ma=75|su=72|lo=25")]
plan = build_adaptive_plan(games, shifts, "chinese")
assert plan["focus_skill"] == "quality", plan
assert plan["source"] == {"completed_games": 2, "completed_shifts": 1}
assert len(plan["plan"]) == 3
assert plan["plan"][0]["kind"] == "game"
assert plan["plan"][1]["kind"] == "game"
assert plan["plan"][0]["game_type"] != plan["plan"][1]["game_type"]
assert plan["plan"][2]["kind"] == "shift"
assert plan["plan"][2]["action"] == "shift_simulation"
assert plan["policy"]["extra_xp"] is False
assert plan["policy"]["max_answers_unchanged"] is True

starter = build_adaptive_plan([], [], "chinese")
assert starter["focus_skill"] == "vocabulary"
assert starter["confidence"] == "starter"

# A perfect mechanic is rotated behind untried alternatives instead of becoming an XP-farm recommendation.
rotated = build_adaptive_plan([
    SimpleNamespace(game_type="match", score=5, total=5),
    SimpleNamespace(game_type="match", score=5, total=5),
    SimpleNamespace(game_type="mistake", score=3, total=5),
], [], "english")
if rotated["focus_skill"] == "vocabulary":
    assert rotated["plan"][0]["game_type"] != "match"

# API is authenticated and user-scoped for both persistent data sources.
for marker in [
    '@router.get("/api/adaptive-training/plan")',
    "user: Any = Depends(current_user)",
    "game_session_model.user_id == user.id",
    "practice_result_model.user_id == user.id",
    "game_session_model.status == \"completed\"",
    "practice_result_model.kind == SHIFT_KIND",
    "build_adaptive_plan(game_rows, shift_rows, language)",
    "weakest_skill_then_different_mechanic",
]:
    assert marker in ROUTER, marker
for forbidden in ["award_xp", "XPEvent", "/api/gamification/spend", "spendable_xp", "require_roles(\"manager\""]:
    assert forbidden not in ROUTER, forbidden

# Router is modular, fail-closed, before StaticFiles and part of the critical route contract.
for marker in [
    '("GET", "/api/adaptive-training/plan")',
    "application.router.routes.insert(insert_at, route)",
    "router_module_owned",
]:
    assert marker in BRIDGE, marker
assert '("GET", "/api/adaptive-training/plan")' in CONTRACTS
assert "bind_adaptive_training_router(module, application)" in RUNTIME
assert "ADAPTIVE_TRAINING_ROUTER_BINDING_REPORT" in RUNTIME
assert "ADAPTIVE_TRAINING_ROUTER_BINDING_REPORT" in ASGI

# UI appears in Games and after a result, starts existing games/Shift Simulation, and adds no XP path.
for marker in [
    'frontend.register("adaptive-training-v627"',
    "ADAPTIVE TRAINING LOOP · v6.0.27",
    "Персональный маршрут следующей тренировки",
    "Следующий шаг после результата",
    "/api/adaptive-training/plan?language=",
    'frontend.get("game-lab-v618")',
    "data-v624-start",
    "Дополнительный XP: <b>нет</b>",
    "Max-5 и серверный anti-farm остаются без изменений",
]:
    assert marker in FRONTEND, marker
assert ".v627-panel" in CSS and ".v627-step" in CSS and "@media(max-width:820px)" in CSS
assert "/adaptive_training_v627.css" in INDEX
assert "/frontend/adaptive_training_v627.js" in INDEX
assert INDEX.index("team_leaderboard_v626.js") < INDEX.index("adaptive_training_v627.js") < INDEX.index("frontend/boot.js")
assert "'adaptive-training-v627'" in BOOT
assert "pilotCandidate: 'v6.0.27'" in BOOT

subprocess.run(["node", "--check", str(ROOT / "static/frontend/adaptive_training_v627.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.27 adds a user-scoped adaptive game + Shift Simulation loop without a new XP path")
