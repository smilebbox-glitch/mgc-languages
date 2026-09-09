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
    stage_d_i18n_path = ROOT / "static/frontend/game_world_stage_d_i18n_v630.js"
    stage_e_path = ROOT / "static/frontend/factory_journey_v2_v630.js"
    source = localization_path.read_text(encoding="utf-8")
    stage_d_i18n = stage_d_i18n_path.read_text(encoding="utf-8")
    stage_e = stage_e_path.read_text(encoding="utf-8")
    index = (ROOT / "static/index.html").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.30.json").read_text(encoding="utf-8"))
    changelog = (ROOT / "CHANGELOG_v6.0.30.md").read_text(encoding="utf-8")

    require("const GAME_TITLES" in source, "Chinese game title map is missing")
    for game_id in sorted(EXPECTED_GAMES):
        require(f"{game_id}:" in source, f"Chinese title/pinyin missing for game: {game_id}")

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

    stage_d_required_pairs = {
        "PROCESS LIVE": "生产过程 · 运行中",
        "TORQUE VERIFY": "扭矩确认",
        "SAFETY INTERLOCK": "安全联锁",
        "AGV ROUTE": "AGV 路线",
        "CMM PROBE": "三坐标测头",
        "CONTROL ROOM": "控制室",
        "PART INSTALL": "部件安装",
        "SURFACE SCAN": "表面扫描",
    }
    for english, chinese in stage_d_required_pairs.items():
        require(english in stage_d_i18n, f"Stage D process label not mapped: {english}")
        require(chinese in stage_d_i18n, f"Stage D Chinese replacement missing for: {english}")

    stage_e_markers = {
        "Supplier": "供应商",
        "Logistics": "物流",
        "Welding": "焊装",
        "Paint": "涂装",
        "Assembly": "总装",
        "Quality": "质量",
        "Engineering": "工程",
        "SHIFT SIMULATION": "班次模拟",
        "CURRENT INCIDENT": "当前事件",
        "LINE STATUS": "当前状态",
    }
    for english, chinese in stage_e_markers.items():
        require(english in stage_e, f"Stage E source label missing: {english}")
        require(chinese in stage_e, f"Stage E Chinese label missing: {english}")

    for incident in (
        "供应商询问最新图纸版本", "24号工位即将缺料", "焊接机器人已停止", "涂装面板出现异常",
        "前保险杠紧固需要确认", "间隙测量需要公差判定", "生产线发现图纸与BOM不一致",
    ):
        require(incident in stage_e, f"Stage E Chinese incident missing: {incident}")

    require("question-pinyin gw30-zh-title-pinyin" in source, "Pinyin title presentation is missing")
    require("snapshot().language === 'chinese'" in source, "Localization must be scoped to Chinese mode")
    require("snapshot().language === 'chinese'" in stage_d_i18n, "Stage D localization must be scoped to Chinese mode")
    require("snapshot().language === 'chinese'" in stage_e, "Stage E localization must be scoped to Chinese mode")
    require("WeakMap" in source, "Localization must preserve original DOM text for reversible language switching")
    require("WeakMap" in stage_d_i18n, "Stage D localization must preserve original process labels")

    forbidden = [
        "submitAnswer(",
        "/api/games/",
        "fetch(",
        "awarded_xp",
        "spendable_xp",
        "gameAnswersV618.push",
    ]
    for layer_name, layer_source in (
        ("Chinese localization", source),
        ("Stage D localization", stage_d_i18n),
        ("Stage E Factory Journey", stage_e),
    ):
        for marker in forbidden:
            require(marker not in layer_source, f"{layer_name} must not own scoring/API state: {marker}")

    stage_c = index.find('/frontend/game_world_stage_c_v630.js')
    stage_d = index.find('/frontend/game_world_stage_d_v630.js')
    stage_d_i18n_pos = index.find('/frontend/game_world_stage_d_i18n_v630.js')
    stage_e_pos = index.find('/frontend/factory_journey_v2_v630.js')
    localization = index.find('/frontend/game_chinese_localization_v630.js')
    require(stage_c >= 0 and stage_d > stage_c, "Stage D must load after Stage C")
    require(stage_d_i18n_pos > stage_d, "Stage D localization must load after Stage D motion")
    require(stage_e_pos > stage_d_i18n_pos, "Stage E must load after Stage D presentation layer")
    require(localization > stage_e_pos, "General Chinese localization must remain last among Game World presentation layers")

    contract = manifest["game_world"].get("chinese_localization") or {}
    expected_scope = {
        "all-20-games", "stage-a", "stage-b", "stage-c", "stage-d", "stage-e",
        "arcade-mastery", "xp", "quiz", "roleplay", "course30",
    }
    require(set(contract.get("scope", [])) == expected_scope, "Localization scope drifted")
    require(contract.get("presentation_only") is True, "Localization must remain presentation-only")
    require(contract.get("canonical_answer_values") == "unchanged", "Canonical answers must remain unchanged")
    require(contract.get("scoring_path") == "unchanged", "Scoring path must remain unchanged")
    require(contract.get("pinyin_game_titles") is True, "Pinyin title contract is missing")
    require(contract.get("pinyin_quiz_choices_when_chinese") is True, "Chinese quiz-choice pinyin contract is missing")
    require("stage-d-process-motion-labels" in contract.get("targets", []), "Stage D localization target missing")
    require("stage-e-factory-journey-incidents" in contract.get("targets", []), "Stage E localization target missing")
    for target in ("arcade-mastery-profile", "xp-and-progress-ui", "quiz-ui-and-chinese-answer-pinyin", "roleplay-ui", "course30-ui"):
        require(target in contract.get("targets", []), f"Chinese learning localization target missing: {target}")
    require("static/frontend/game_chinese_localization_v630.js" in manifest["game_world"]["assets"], "Localization asset missing from manifest")
    require("static/frontend/game_world_stage_d_i18n_v630.js" in manifest["game_world"]["assets"], "Stage D localization asset missing from manifest")
    require("static/frontend/factory_journey_v2_v630.js" in manifest["game_world"]["assets"], "Stage E asset missing from manifest")
    require("static/frontend/chinese_learning_surface_v630.js" in manifest["game_world"]["assets"], "Chinese learning-surface asset missing from manifest")
    require("Chinese Game Localization Audit" in changelog, "Localization audit is missing from changelog")
    require("Chinese Learning Surface + Level Uniqueness" in changelog, "Learning-surface changelog entry is missing")
    require("Stage D — Process-Specific Motion" in changelog, "Stage D changelog entry is missing")
    require("Stage E — Factory Journey 2.0" in changelog, "Stage E changelog entry is missing")

    print("v6.0.30 Chinese games + learning-surface localization regression: OK")


if __name__ == "__main__":
    main()
