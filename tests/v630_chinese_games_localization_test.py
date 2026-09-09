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
    source = (ROOT / "static/frontend/game_chinese_localization_v630.js").read_text(encoding="utf-8")
    stage_e = (ROOT / "static/frontend/factory_journey_v2_v630.js").read_text(encoding="utf-8")
    index = (ROOT / "static/index.html").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "RELEASE_MANIFEST_v6.0.30.json").read_text(encoding="utf-8"))

    require("const GAME_TITLES_RU" in source, "Russian game title map is missing")
    for game_id in sorted(EXPECTED_GAMES):
        require(f"{game_id}:" in source, f"Russian title missing for game: {game_id}")

    for title in (
        "Сопоставление слов", "Аудиоспринт", "Точная проверка", "Конструктор фраз",
        "Детали автомобиля", "Собери автомобиль", "Маршрут по заводу", "Выбор инструмента",
        "Детектор дефектов", "Найди опасность", "Контроль качества", "Логистический поток",
        "Канбан", "Собери BOM", "Допуск или NOK?", "Быстрый ответ", "Гараж памяти",
        "Лишний термин", "Рабочий диалог", "Ситуация на смене",
    ):
        require(title in source, f"Russian game title missing: {title}")

    for ui_text in (
        "ИГРОВОЙ ПРОФИЛЬ · КАРТА НАВЫКОВ", "ИНСТРУКТАЖ", "ХОД ЗАДАНИЯ",
        "ЗАДАНИЕ ЗАВЕРШЕНО", "СБОРОЧНАЯ ЛИНИЯ · РАБОТАЕТ", "ПРОВЕРКА МОМЕНТА",
        "БЛОКИРОВКА БЕЗОПАСНОСТИ", "МАРШРУТ AGV", "ЩУП CMM", "ДИСПЕТЧЕРСКАЯ",
    ):
        require(ui_text in source, f"Russian game UI marker missing: {ui_text}")

    # Factory Journey incidents are learning material: Chinese + pinyin + Russian meaning remain available.
    for incident in (
        "供应商询问最新图纸版本", "24号工位即将缺料", "焊接机器人已停止", "涂装面板出现异常",
        "前保险杠紧固需要确认", "间隙测量需要公差判定", "生产线发现图纸与BOM不一致",
    ):
        require(incident in stage_e, f"Chinese learning incident missing: {incident}")
    require("incidentPy" in stage_e, "Factory Journey pinyin is missing")
    require("incidentRu" in stage_e, "Factory Journey Russian meaning is missing")

    require("data-game-ui-language', 'ru'" in source, "Russian game UI contract marker is missing")
    require("data-game-learning-language" in source, "Learning-language marker is missing")
    require(".game-choice" in source and ".question-pinyin" in source, "Learning nodes must be excluded from UI translation")
    require("gw30-zh-title-pinyin" in source and ".remove()" in source, "Old Chinese title pinyin must be removed")

    forbidden = ["submitAnswer(", "/api/games/", "fetch(", "awarded_xp", "spendable_xp", "gameAnswersV618.push"]
    for marker in forbidden:
        require(marker not in source, f"Presentation layer must not own scoring/API state: {marker}")

    localization = index.find('/frontend/game_chinese_localization_v630.js')
    surface = index.find('/frontend/chinese_learning_surface_v630.js')
    require(localization >= 0 and surface > localization, "Learning-content pinyin layer must load after Russian game UI layer")

    contract = manifest["game_world"].get("chinese_localization") or {}
    require(contract.get("presentation_only") is True, "Localization must remain presentation-only")
    require(contract.get("canonical_answer_values") == "unchanged", "Canonical answers must remain unchanged")
    require(contract.get("scoring_path") == "unchanged", "Scoring path must remain unchanged")
    require(contract.get("pinyin_quiz_choices_when_chinese") is True, "Chinese quiz-choice pinyin contract is missing")

    print("v6.0.30 Russian UI + Chinese/pinyin learning-content regression: OK")


if __name__ == "__main__":
    main()
