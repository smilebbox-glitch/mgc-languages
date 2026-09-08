from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mgc.routers.shift_analytics import ShiftSimulationPayload, encode_shift_topic  # noqa: E402
from mgc.routers.team_analytics import _best_rows, summarize_team_shift_rows  # noqa: E402

ROUTER = (ROOT / "mgc/routers/team_analytics.py").read_text(encoding="utf-8")
BRIDGE = (ROOT / "mgc_core/team_analytics_router_bridge.py").read_text(encoding="utf-8")
SHIFT_ROUTER = (ROOT / "mgc/routers/shift_analytics.py").read_text(encoding="utf-8")
RUNTIME = (ROOT / "mgc_core/runtime.py").read_text(encoding="utf-8")
ASGI = (ROOT / "asgi.py").read_text(encoding="utf-8")
CONTRACTS = (ROOT / "mgc_core/contracts.py").read_text(encoding="utf-8")
FRONTEND = (ROOT / "static/frontend/team_leaderboard_v626.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/team_leaderboard_v626.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# Ranking contract: score desc, then faster completion; one best attempt per employee.
now = datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc)
def game(user_id: int, name: str, score: int, seconds: int, offset: int = 0):
    started = now + timedelta(minutes=offset)
    return (
        SimpleNamespace(user_id=user_id, score=score, total=5, created_at=started, completed_at=started + timedelta(seconds=seconds)),
        SimpleNamespace(display_name=name),
    )

ordered, position = _best_rows([
    game(1, "Анна", 5, 45), game(1, "Анна", 5, 38, 2),
    game(2, "Борис", 5, 50), game(3, "Виктор", 4, 20),
], current_user_id=2)
assert [row["display_name"] for row in ordered] == ["Анна", "Борис", "Виктор"]
assert ordered[0]["duration_ms"] == 38_000
assert ordered[0]["rank"] == 1 and ordered[1]["rank"] == 2
assert ordered[1]["is_current_user"] is True
assert position == 2

# Manager aggregate is balanced by participant rather than letting one heavy user dominate the team signal.
def shift_row(user_id: int, pc: int, pr: int, pj: int, lang: int, line: int, quality: int, material: int, supplier: int, load: int):
    payload = ShiftSimulationPayload(
        session_id=f"shift-user-{user_id}-{pc}", language="chinese", production_control=pc,
        prioritization=pr, production_judgement=pj, language_score=lang,
        total_score=round((pc + pr + pj + lang) / 4), weakest_dimension="language",
        factory_weakest="supplier", line=line, quality=quality, material=material,
        supplier=supplier, load=load,
    )
    return (SimpleNamespace(user_id=user_id, score=payload.total_score, topic=encode_shift_topic(payload), language="chinese"), SimpleNamespace(display_name=str(user_id)))

team = summarize_team_shift_rows([
    shift_row(1, 90, 80, 85, 60, 90, 80, 75, 55, 30),
    shift_row(1, 88, 78, 83, 58, 88, 78, 74, 54, 32),
    shift_row(2, 70, 68, 72, 50, 72, 70, 68, 48, 45),
], eligible_users=4)
assert team["eligible_users"] == 4
assert team["participants"] == 2
assert team["completed_shifts"] == 3
assert team["participation_percent"] == 50
assert team["weakest_dimension"] == "language"
assert team["language_mix"]["chinese"] == 3

# Role and privacy contracts.
for marker in [
    '@router.get("/api/manager/shift-analytics")',
    'Depends(require_roles("manager", "admin"))',
    'requested and requested != user.department',
    'Руководитель может видеть агрегаты только своего подразделения',
    '@router.get("/api/leaderboards/games/{game_type}")',
    '@router.get("/api/leaderboards/shifts")',
    'user_model.department == user.department',
    'limit: int = Query(default=10, ge=1, le=10)',
    'score_desc_then_time_asc_best_attempt_per_user',
    'не является HR-рейтингом',
]:
    assert marker in ROUTER, marker
for forbidden in ["award_xp", "XPEvent", "/api/gamification/spend", "spendable_xp"]:
    assert forbidden not in ROUTER, forbidden

# Shift payload can carry a bounded duration for timed shift leaderboard rows without a schema migration.
assert "duration_ms: int | None" in SHIFT_ROUTER
assert 'values.append(f"du={int(payload.duration_ms)}")' in SHIFT_ROUTER
assert '"duration_ms": duration_ms' in SHIFT_ROUTER

# Router is runtime-bound before StaticFiles and included in the fail-closed route contract.
for marker in [
    '("GET", "/api/manager/shift-analytics")',
    '("GET", "/api/leaderboards/games/{game_type}")',
    '("GET", "/api/leaderboards/shifts")',
    "application.router.routes.insert(insert_at, route)",
]:
    assert marker in BRIDGE, marker
    assert marker in CONTRACTS or "application.router.routes.insert" in marker
assert "bind_team_analytics_router(module, application)" in RUNTIME
assert "TEAM_ANALYTICS_ROUTER_BINDING_REPORT" in RUNTIME
assert "TEAM_ANALYTICS_ROUTER_BINDING_REPORT" in ASGI

# UI: Top-10 appears after completed timed games; manager view remains aggregate-only.
for marker in [
    'frontend.register("team-leaderboard-v626"',
    "TOP 10 · SCORE + TIME",
    "Сначала выше результат, при равных очках — меньшее время",
    "лучшая попытка сотрудника",
    "ваше место",
    "TEAM ANALYTICS · v6.0.26",
    "Агрегаты по Shift Simulation без рейтинга сотрудников",
    "/api/manager/shift-analytics?language=",
    "/api/leaderboards/games/",
    "Учебный рейтинг. Не используется как HR-оценка",
]:
    assert marker in FRONTEND, marker
assert ".v626-leaderboard" in CSS and ".v626-team-panel" in CSS and ".v626-rank-row.current" in CSS

assert "/team_leaderboard_v626.css" in INDEX
assert "/frontend/team_leaderboard_v626.js" in INDEX
assert INDEX.index("manager_admin.js") < INDEX.index("team_leaderboard_v626.js") < INDEX.index("frontend/boot.js")
assert "'team-leaderboard-v626'" in BOOT
candidate = re.search(r"pilotCandidate: 'v6\.0\.(\d+)'", BOOT)
assert candidate and int(candidate.group(1)) >= 26

subprocess.run(["node", "--check", str(ROOT / "static/frontend/team_leaderboard_v626.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.26 adds department-scoped manager analytics and Top-10 score/time leaderboards without changing XP")
