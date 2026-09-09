from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_GAMES = {
    "match", "listening", "mistake", "phrase", "hotspot",
    "assembly_order", "shop_route", "tool_select", "defect_detective", "safety_spot",
    "quality_gate", "logistics_route", "kanban", "bom_builder", "spec_check",
    "rapid_recall", "memory_pairs", "odd_one_out", "dialogue_choice", "shift_incident",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    localization_path = ROOT / "static/frontend/game_chinese_localization_v630.js"
    source = localization_path.read_text(encoding="utf-8")
    index = (ROOT / "static/index.html").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.30.json").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG_v6.0.30.md").read_text(encoding="utf-8")

    require("const GAME_TITLES" in source, "Chinese game title map is missing")
    for game_id in sorted(EXPECTED_GAMES):
        require(f"{game_id}:" in source, f"Chinese title/pinyin missing for game: {game_id}")

    # Regression targets reported by the pilot: these English-only surfaces must have Chinese mappings.
    required_pairs = {
        "PASS": "合格",
        "REWORK": "返工",
        "HOLD": "暂停",
        "Receiving": "收货",
        "Put-away": "入库",
        "Line replenishment": "线边补货",
        "Customs": "海关",
        "Shortage signal": "缺料信号",
        "bumper": "保险杠",
        "instrument panel": "仪表板",
        "wiring harness": "线束",
        "returnable container": "可循环容器",
        "Gap": "间隙",
        "Flush": "面差",
        "Torque": "扭矩",
        "Film thickness": "漆膜厚度",
        "Pressure": "压力",
        "MISSION BRIEFING": "任务简报",
        "MISSION FLOW": "任务进度",
        "MISSION COMPLETE": "任务完成",
        "GAME WORLD": "游戏世界",
        "Factory Hub": "工厂中心",
    }
    for english, chinese in required_pairs.items():
        require(repr(english) in source or f"'{english}'" in source, f"English leakage target not mapped: {english}")
        require(chinese in source, f"Chinese replacement missing for: {english}")

    require("question-pinyin gw30-zh-title-pinyin" in source, "Pinyin title presentation is missing")
    require("snapshot().language === 'chinese'" in source, "Localization must be scoped to Chinese mode")
    require("WeakMap" in source, "Localization must preserve original DOM text for reversible language switching")

    # This file is strictly presentation-only. It may not introduce a parallel game/scoring path.
    forbidden = [
        "submitAnswer(",
        "/api/games/",
        "fetch(",
        "awarded_xp",
        "spendable_xp",
        "gameAnswersV618.push",
    ]
    for marker in forbidden:
        require(marker not in source, f"Localization layer must not own scoring/API state: {marker}")

    stage_c = index.find('/frontend/game_world_stage_c_v630.js')
    localization = index.find('/frontend/game_chinese_localization_v630.js')
    require(stage_c >= 0 and localization > stage_c, "Chinese localization must load after Stage C")

    contract = manifest["game_world"].get("chinese_localization") or {}
    require(contract.get("scope") == ["all-20-games", "stage-a", "stage-b", "stage-c"], "Localization scope drifted")
    require(contract.get("presentation_only") is True, "Localization must remain presentation-only")
    require(contract.get("canonical_answer_values") == "unchanged", "Canonical answers must remain unchanged")
    require(contract.get("scoring_path") == "unchanged", "Scoring path must remain unchanged")
    require(contract.get("pinyin_game_titles") is True, "Pinyin title contract is missing")
    require("static/frontend/game_chinese_localization_v630.js" in manifest["game_world"]["assets"], "Localization asset missing from manifest")
    require("Chinese Game Localization Audit" in changelog, "Localization audit is missing from changelog")

    print("v6.0.30 Chinese games localization regression: OK")


if __name__ == "__main__":
    main()
