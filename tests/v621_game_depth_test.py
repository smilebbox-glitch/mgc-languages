from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPTH = (ROOT / "static/frontend/game_depth_v621.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/game_depth_v621.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
LAB = (ROOT / "static/frontend/game_lab_v618.js").read_text(encoding="utf-8")

# v6.0.21 must deepen the existing 20-game arcade rather than create duplicate games.
GAME_TYPES = [
    "match", "listening", "mistake", "phrase", "hotspot", "assembly_order",
    "shop_route", "tool_select", "defect_detective", "safety_spot", "quality_gate",
    "logistics_route", "kanban", "bom_builder", "spec_check", "rapid_recall",
    "memory_pairs", "odd_one_out", "dialogue_choice", "shift_incident",
]
for game_type in GAME_TYPES:
    assert f"{game_type}:" in DEPTH, game_type
    assert f"{game_type}: {{" in DEPTH, f"missing production context for {game_type}"

# Difficulty is explicit and adaptive across the five-question session.
for level in ["adaptive", "training", "shift", "expert"]:
    assert f"{level}:" in DEPTH, level
assert "Number(index || 0) <= 1" in DEPTH
assert "Number(index || 0) <= 3" in DEPTH
assert "gameDepthDifficulty" in DEPTH
assert "mgc.game-depth.v621.difficulty" in DEPTH
assert "Режим сложности" in DEPTH
assert "3 уровня" in DEPTH

# The requested dedicated automotive production scenes must remain present.
for marker in [
    "v621-paint", "v621-welding", "v621-logistics", "v621-quality",
    "v621-safety", "v621-engineering", "v621-assembly",
]:
    assert marker in DEPTH, marker
    assert marker in CSS, marker
for label in [
    "PAINT BOOTH", "BODY SHOP", "RECEIVING", "QUALITY GATE",
    "ASSEMBLY LINE", "BOM · VARIANT", "FACTS · OWNER",
]:
    assert label in DEPTH, label

# Car Hotspot gets visibly richer while retaining the original clickable zones and answer handlers.
for detail in [
    "v621-roof-line", "v621-belt-line", "v621-rocker", "v621-hood-seam",
    "v621-fender-line", "v621-handle", "v621-grille", "v621-lamp",
    "v621-hub", "v621-wheel-spoke", "v621-pillar",
]:
    assert detail in DEPTH, detail
assert "data-hotspot-zone" in LAB
assert "submitAnswer(button.dataset.hotspotZone)" in LAB

# Expert mode removes selected scaffolding, but does not alter server scoring or the five-answer contract.
assert ".v621-level-expert .hotspot-target small" in CSS
assert ".v621-level-expert .svg-hotspot circle" in CSS
assert "five-answer-badge" in LAB
assert "max 5" in LAB
assert "/api/games/" not in DEPTH

# Assets must load before the boot readiness gate and remain part of the required module contract.
assert "/game_depth_v621.css" in INDEX
assert "/frontend/game_depth_v621.js" in INDEX
assert INDEX.index("game_depth_v621.js") < INDEX.index("frontend/boot.js")
assert "'game-depth-v621'" in BOOT
assert "pilotCandidate: 'v6.0." in BOOT
assert "http://" not in DEPTH and "https://" not in DEPTH

subprocess.run(["node", "--check", str(ROOT / "static/frontend/game_depth_v621.js")], check=True, cwd=ROOT)
subprocess.run(["node", "--check", str(ROOT / "static/frontend/boot.js")], check=True, cwd=ROOT)

print("PASS: v6.0.21 deepens all 20 games with adaptive difficulty, detailed vehicle visuals and dedicated automotive production scenes")
