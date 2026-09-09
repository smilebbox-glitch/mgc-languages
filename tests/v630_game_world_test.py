from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.30.json").read_text(encoding="utf-8"))
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
BOOT = (STATIC / "frontend/boot.js").read_text(encoding="utf-8")
CONFIG = (ROOT / "mgc/config.py").read_text(encoding="utf-8")
WORLD_JS = (STATIC / "frontend/game_world_v630.js").read_text(encoding="utf-8")
WORLD_CSS = (STATIC / "game_world_v630.css").read_text(encoding="utf-8")
STAGE_A_JS = (STATIC / "frontend/game_world_stage_a_v630.js").read_text(encoding="utf-8")
STAGE_A_CSS = (STATIC / "game_world_stage_a_v630.css").read_text(encoding="utf-8")
STAGE_B_JS = (STATIC / "frontend/game_world_stage_b_v630.js").read_text(encoding="utf-8")
STAGE_B_CSS = (STATIC / "game_world_stage_b_v630.css").read_text(encoding="utf-8")
STAGE_C_JS = (STATIC / "frontend/game_world_stage_c_v630.js").read_text(encoding="utf-8")
STAGE_C_CSS = (STATIC / "game_world_stage_c_v630.css").read_text(encoding="utf-8")
STAGE_D_JS = (STATIC / "frontend/game_world_stage_d_v630.js").read_text(encoding="utf-8")
STAGE_D_CSS = (STATIC / "game_world_stage_d_v630.css").read_text(encoding="utf-8")

from mgc.services.practice_games import GAME_TYPES, MAX_GAME_ANSWERS

assert MANIFEST["release"] == "6.0.30", MANIFEST.get("release")
assert MANIFEST["base_release"] == "6.0.29", MANIFEST.get("base_release")
assert MANIFEST["status"] == "game-world-expansion", MANIFEST.get("status")
assert MANIFEST["freeze"] is False
assert MANIFEST["game_contract"]["count"] == 20
assert MANIFEST["game_contract"]["max_answers_per_session"] == 5
assert MANIFEST["game_contract"]["anti_farm"] == "unchanged"
assert list(GAME_TYPES) == MANIFEST["game_contract"]["game_types"], (list(GAME_TYPES), MANIFEST["game_contract"]["game_types"])
assert MAX_GAME_ANSWERS == 5, MAX_GAME_ANSWERS

assert 'APP_VERSION = os.getenv("APP_VERSION", "6.0.30").strip() or "6.0.30"' in CONFIG, "config version"
assert "pilotCandidate: 'v6.0.30'" in BOOT, "boot version"
for asset in (
    "game_world_v630.css", "frontend/game_world_v630.js",
    "game_world_stage_a_v630.css", "frontend/game_world_stage_a_v630.js",
    "game_world_stage_b_v630.css", "frontend/game_world_stage_b_v630.js",
    "game_world_stage_c_v630.css", "frontend/game_world_stage_c_v630.js",
    "game_world_stage_d_v630.css", "frontend/game_world_stage_d_v630.js",
):
    assert asset in INDEX, f"Game World asset not loaded: {asset}"

world_block = re.search(r"const GAME_WORLD = Object\.freeze\(\{(.*?)\}\);", WORLD_JS, flags=re.S)
assert world_block, "GAME_WORLD mapping not found"
world_source = world_block.group(1)
for game_type in MANIFEST["game_contract"]["game_types"]:
    assert re.search(rf"(?:^|\s|,)['\"]?{re.escape(game_type)}['\"]?\s*:", world_source), f"missing Game World mapping: {game_type}"

for scene in MANIFEST["game_world"]["scenes"]:
    assert scene in WORLD_JS or scene in WORLD_CSS, f"missing scene: {scene}"

for marker in (
    "prefers-reduced-motion", "gw30-conveyor", "gw30-car", "gw30-robot", "gw30-hud",
    "Базовый", "Средний", "Продвинутый",
):
    assert marker in WORLD_CSS or marker in WORLD_JS, f"missing Game World marker: {marker}"

stage_a = MANIFEST["game_world"]["stage_a"]
assert stage_a["scope"] == ["assembly", "welding", "paint", "logistics"]
assert stage_a["production_context_only"] is True
assert stage_a["scoring_path"] == "unchanged"
assert stage_a["answer_controls"] == "canonical-game-lab"
assert len(stage_a["covered_games"]) == 12
stage_a_block = re.search(r"const STAGE_A = Object\.freeze\(\{(.*?)\}\);", STAGE_A_JS, flags=re.S)
assert stage_a_block, "STAGE_A mapping not found"
stage_a_source = stage_a_block.group(1)
for game_type in stage_a["covered_games"]:
    assert re.search(rf"(?:^|\s|,)['\"]?{re.escape(game_type)}['\"]?\s*:", stage_a_source), f"missing Stage A mapping: {game_type}"
for marker in (
    "gw30a-assembly-line", "gw30a-weld-cell", "gw30a-paint-panel", "gw30a-flow-map",
    "gw30a-hotspot-enhanced", "gw30a-order-enhanced", "gw30a-tools-enhanced",
    "gw30a-defect-enhanced", "gw30a-safety-enhanced", "gw30a-route-enhanced",
    "gw30a-kanban-enhanced", "prefers-reduced-motion",
):
    assert marker in STAGE_A_JS or marker in STAGE_A_CSS, f"missing Stage A marker: {marker}"

stage_b = MANIFEST["game_world"]["stage_b"]
assert stage_b["scope"] == ["quality", "engineering"]
assert stage_b["production_context_only"] is True
assert stage_b["scoring_path"] == "unchanged"
assert stage_b["answer_controls"] == "canonical-game-lab"
assert stage_b["covered_games"] == ["mistake", "quality_gate", "spec_check", "bom_builder", "odd_one_out"]
stage_b_block = re.search(r"const STAGE_B = Object\.freeze\(\{(.*?)\}\);", STAGE_B_JS, flags=re.S)
assert stage_b_block, "STAGE_B mapping not found"
stage_b_source = stage_b_block.group(1)
for game_type in stage_b["covered_games"]:
    assert re.search(rf"(?:^|\s|,)['\"]?{re.escape(game_type)}['\"]?\s*:", stage_b_source), f"missing Stage B mapping: {game_type}"
for marker in (
    "gw30b-quality-cell", "gw30b-cmm", "gw30b-tolerance", "gw30b-status-stack",
    "gw30b-engineering-board", "gw30b-drawing", "gw30b-bom-tree", "gw30b-thread",
    "gw30b-quality-gauge-enhanced", "gw30b-spec-enhanced", "gw30b-bom-enhanced",
    "prefers-reduced-motion",
):
    assert marker in STAGE_B_JS or marker in STAGE_B_CSS, f"missing Stage B marker: {marker}"

stage_c = MANIFEST["game_world"]["stage_c"]
assert stage_c["scope"] == ["all-20-games"]
assert stage_c["production_context_only"] is True
assert stage_c["scoring_path"] == "unchanged"
assert stage_c["answer_controls"] == "canonical-game-lab"
assert stage_c["covered_games"] == MANIFEST["game_contract"]["game_types"]
assert stage_c["per_answer_correctness_before_finish"] is False
assert stage_c["result_source"] == "canonical-server-finish"
for game_type in stage_c["covered_games"]:
    assert re.search(rf"\b{re.escape(game_type)}\s*:\s*\{{brief:", STAGE_C_JS), f"missing Stage C briefing: {game_type}"
for marker in (
    "gw30c-onboarding", "gw30c-rail", "gw30c-recorded", "gw30c-result-hero",
    "MISSION BRIEFING", "MISSION COMPLETE", "Ответ зафиксирован", "prefers-reduced-motion",
):
    assert marker in STAGE_C_JS or marker in STAGE_C_CSS, f"missing Stage C marker: {marker}"

stage_d = MANIFEST["game_world"]["stage_d"]
assert stage_d["scope"] == ["all-20-games"]
assert stage_d["production_motion_only"] is True
assert stage_d["scoring_path"] == "unchanged"
assert stage_d["answer_controls"] == "canonical-game-lab"
assert stage_d["covered_games"] == MANIFEST["game_contract"]["game_types"]
assert stage_d["per_answer_correctness_before_finish"] is False
assert stage_d["motion_families"] == ["assembly", "welding", "paint", "logistics", "quality", "engineering", "factory"]
stage_d_block = re.search(r"const PROCESS_BY_GAME = Object\.freeze\(\{(.*?)\}\);", STAGE_D_JS, flags=re.S)
assert stage_d_block, "Stage D PROCESS_BY_GAME mapping not found"
stage_d_source = stage_d_block.group(1)
for game_type in stage_d["covered_games"]:
    assert re.search(rf"(?:^|\s|,)['\"]?{re.escape(game_type)}['\"]?\s*:", stage_d_source), f"missing Stage D motion profile: {game_type}"
for marker in (
    "gw30d-rig-assembly", "gw30d-rig-welding", "gw30d-rig-paint", "gw30d-rig-logistics",
    "gw30d-rig-quality", "gw30d-rig-engineering", "gw30d-rig-factory",
    "gw30d-driver", "gw30d-weld-point", "gw30d-spray-gun", "gw30d-agv", "gw30d-cmm-gantry",
    "gw30d-data-link", "gw30d-andon", "prefers-reduced-motion",
):
    assert marker in STAGE_D_JS or marker in STAGE_D_CSS, f"missing Stage D marker: {marker}"

# Stages A/B/C/D are visual/context layers. They may observe canonical controls, but they must
# not create alternate answer/scoring/API paths.
for layer_name, source in (("Stage A", STAGE_A_JS), ("Stage B", STAGE_B_JS), ("Stage C", STAGE_C_JS), ("Stage D", STAGE_D_JS)):
    for forbidden in (
        "submitAnswer(", "/api/games/", "spendable_xp", "awarded_xp", "MAX_GAME_ANSWERS =", "fetch(",
    ):
        assert forbidden not in source, f"{layer_name} must not own gameplay/scoring path: {forbidden}"

for rel in MANIFEST["critical_files"]:
    path = ROOT / rel
    assert path.is_file() and path.stat().st_size > 0, f"critical file missing: {rel}"

for script in (
    "frontend/game_world_v630.js", "frontend/game_world_stage_a_v630.js",
    "frontend/game_world_stage_b_v630.js", "frontend/game_world_stage_c_v630.js",
    "frontend/game_world_stage_d_v630.js", "frontend/boot.js",
):
    subprocess.run(["node", "--check", str(STATIC / script)], check=True, cwd=ROOT)

print("PASS: v6.0.30 Game World Stages A+B+C+D deepen all 20 games with process motion while preserving max-five, anti-farm and canonical scoring/API boundaries")
