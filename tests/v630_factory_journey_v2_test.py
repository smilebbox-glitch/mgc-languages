from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"

MANIFEST = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.30.json").read_text(encoding="utf-8"))
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
SOURCE = (STATIC / "frontend/factory_journey_v2_v630.js").read_text(encoding="utf-8")
CSS = (STATIC / "factory_journey_v2_v630.css").read_text(encoding="utf-8")

EXPECTED_STAGE_IDS = ["supplier", "logistics", "welding", "paint", "assembly", "quality", "engineering"]
EXPECTED_GAMES = ["dialogue_choice", "logistics_route", "shift_incident", "defect_detective", "tool_select", "spec_check", "bom_builder"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    contract = MANIFEST["game_world"].get("stage_e") or {}
    require(contract.get("scope") == EXPECTED_STAGE_IDS, "Stage E scope drifted")
    require(contract.get("journey_orchestration_only") is True, "Stage E must remain orchestration-only")
    require(contract.get("scoring_path") == "unchanged", "Stage E scoring path changed")
    require(contract.get("launch_path") == "canonical-game-lab-startGame", "Stage E must launch canonical Game Lab")
    require(contract.get("progress_source") == "canonical-game-engagement-progress", "Stage E progress must come from canonical engagement")
    require(contract.get("stage_count") == 7, "Factory Journey 2.0 must contain seven stages")
    require(contract.get("covered_games") == EXPECTED_GAMES, "Factory Journey 2.0 game mapping drifted")
    require(contract.get("per_answer_correctness_before_finish") is False, "Stage E may not infer per-answer correctness")
    require(contract.get("chinese_incident_labels") is True, "Stage E Chinese incident contract missing")

    stage_block = re.search(r"const STAGES = Object\.freeze\(\[(.*?)\]\);", SOURCE, flags=re.S)
    require(stage_block is not None, "Factory Journey 2.0 STAGES mapping missing")
    stage_source = stage_block.group(1)
    require(stage_source.count("id:") == 7, "Factory Journey 2.0 must define exactly seven stage objects")
    for stage_id, game in zip(EXPECTED_STAGE_IDS, EXPECTED_GAMES):
        require(f"id:'{stage_id}'" in stage_source, f"Missing Factory Journey stage: {stage_id}")
        require(f"game:'{game}'" in stage_source, f"Missing canonical game mapping: {game}")
        require(game in MANIFEST["game_contract"]["game_types"], f"Stage E references non-canonical game: {game}")

    require("lab.startGame(stage.game)" in SOURCE, "Factory Journey must launch the canonical Game Lab")
    require("api.progress()" in SOURCE, "Factory Journey must read canonical engagement progress")
    require("Math.min(5" in SOURCE, "Journey score presentation must remain bounded by the canonical five-answer session")

    for marker in (
        "factory-journey-v2-v630", "fj2-route", "fj2-incident", "fj2-car", "fj2-twin",
        "DIGITAL VEHICLE", "FACTORY TWIN", "SHIFT SIMULATION", "prefers-reduced-motion",
    ):
        require(marker in SOURCE or marker in CSS, f"Factory Journey 2.0 visual marker missing: {marker}")

    for chinese_marker in (
        "供应商询问最新图纸版本", "24号工位即将缺料", "焊接机器人已停止", "涂装面板出现异常",
        "前保险杠紧固需要确认", "间隙测量需要公差判定", "生产线发现图纸与BOM不一致",
    ):
        require(chinese_marker in SOURCE, f"Factory Journey Chinese incident missing: {chinese_marker}")

    for pinyin_marker in (
        "gōngyìngshāng", "wùliú", "hànzhuāng", "túzhuāng", "zǒngzhuāng", "zhìliàng", "gōngchéng",
    ):
        require(pinyin_marker in SOURCE, f"Factory Journey pinyin label missing: {pinyin_marker}")

    forbidden = (
        "submitAnswer(", "/api/games/", "fetch(", "awarded_xp", "spendable_xp",
        "gameAnswersV618.push", "MAX_GAME_ANSWERS =",
    )
    for marker in forbidden:
        require(marker not in SOURCE, f"Stage E must not own scoring/API state: {marker}")

    css_pos = INDEX.find('/factory_journey_v2_v630.css')
    js_pos = INDEX.find('/frontend/factory_journey_v2_v630.js')
    stage_d_pos = INDEX.find('/frontend/game_world_stage_d_i18n_v630.js')
    localization_pos = INDEX.find('/frontend/game_chinese_localization_v630.js')
    require(css_pos >= 0, "Factory Journey 2.0 CSS not loaded")
    require(js_pos > stage_d_pos >= 0, "Factory Journey 2.0 must load after Stage D")
    require(localization_pos > js_pos, "General Chinese localization should remain last among Game World presentation layers")

    assets = MANIFEST["game_world"]["assets"]
    require("static/factory_journey_v2_v630.css" in assets, "Factory Journey CSS missing from manifest")
    require("static/frontend/factory_journey_v2_v630.js" in assets, "Factory Journey JS missing from manifest")

    subprocess.run(["node", "--check", str(STATIC / "frontend/factory_journey_v2_v630.js")], check=True, cwd=ROOT)
    print("PASS: v6.0.30 Stage E Factory Journey 2.0 links seven automotive incidents to canonical Game Lab sessions without changing scoring, XP or API")


if __name__ == "__main__":
    main()
