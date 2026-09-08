from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTERY = (ROOT / "static/frontend/arcade_mastery_v620.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/arcade_mastery_v620.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")

# Mastery is an additive analytics/engagement layer over the existing arcade.
assert "frontend.get('game-lab-v618')" in MASTERY
assert "frontend.get('game-engagement-v618')" in MASTERY
assert "engagement().progress()" in MASTERY
assert "gameLab().startGame(gameId)" in MASTERY

# Launches from the skill map must also be visible to the existing engagement tracker.
assert MASTERY.count("data-start-v618-game") >= 2
assert "data-master-game" in MASTERY

# Seven distinct competency tracks must remain visible and mapped to real game types.
for skill in [
    "vocabulary", "listening", "production", "quality",
    "logistics", "engineering", "communication",
]:
    assert f"id:'{skill}'" in MASTERY, skill
for game_type in [
    "match", "listening", "assembly_order", "defect_detective",
    "logistics_route", "bom_builder", "dialogue_choice",
]:
    assert f"'{game_type}'" in MASTERY, game_type

# Department priorities and adaptive weak-skill recommendation are required.
for group in ["paint", "logistics", "body", "assembly", "quality", "rd", "purchasing", "default"]:
    assert f"{group}:" in MASTERY, group
assert "weakestRow" in MASTERY
assert "nextGameForSkill" in MASTERY
assert "СЛЕДУЮЩИЙ АПГРЕЙД" in MASTERY
assert "Тренировать слабое место" in MASTERY

# Mastery score blends best-result accuracy and breadth, not just raw XP.
assert "accuracy * 0.75" in MASTERY
assert "coverage * 0.25" in MASTERY
assert "stats.overall" in MASTERY
assert "stats.focus" in MASTERY

# Achievements are bounded to meaningful learning milestones.
for marker in ["Первый заезд", "Исследователь", "Полный гараж", "Чистая смена", "Стабильность", "Цеховой специалист"]:
    assert marker in MASTERY, marker
assert "Без искусственного фарма XP" in MASTERY

# Integration and offline UI contract. Historical regressions must not pin a newer
# pilot's exact version; the active release owns the exact pilotCandidate assertion.
assert "/arcade_mastery_v620.css" in INDEX
assert "/frontend/arcade_mastery_v620.js" in INDEX
assert INDEX.index("arcade_mastery_v620.js") < INDEX.index("frontend/boot.js")
assert "'arcade-mastery-v620'" in BOOT
assert "pilotCandidate:" in BOOT
assert ".arcade-mastery-v620" in CSS
assert ".mastery-ring" in CSS
assert ".mastery-skill-card" in CSS
assert "http://" not in MASTERY and "https://" not in MASTERY

subprocess.run(["node", "--check", str(ROOT / "static/frontend/arcade_mastery_v620.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.20 mastery patch adds 7-skill competency mapping, tracked launches, department focus, adaptive next-game guidance and achievements")
