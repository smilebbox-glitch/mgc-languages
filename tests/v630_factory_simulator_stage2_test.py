from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
JS = (ROOT / "static/frontend/factory_simulator_stage2_v630.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/factory_simulator_stage2_v630.css").read_text(encoding="utf-8")


def test_stage2_assets_are_loaded_from_optional_boot_layer():
    assert "/factory_simulator_stage2_v630.css" in BOOT
    assert "/frontend/factory_simulator_stage2_v630.js" in BOOT
    assert "loadProductionSimulationEnhancements" in BOOT


def test_three_factory_roles_exist():
    for token in (
        "Оператор", "操作员", "cāozuòyuán", "Operator",
        "Инженер", "工程师", "gōngchéngshī", "Engineer",
        "Team Leader", "班组长", "bānzǔzhǎng"
    ):
        assert token in JS


def test_factory_shift_has_map_and_ten_events_with_timer():
    for stage in ("stamping", "welding", "paint", "assembly", "quality", "dealer"):
        assert f"L('{stage}'" in JS
        assert f'data-stage="{stage}"' in CSS
    assert "session.seconds=720" in JS
    assert "slice(0,10)" in JS
    assert "Factory Shift" in JS
    assert "~12 МИНУТ · 10 СОБЫТИЙ" in JS


def test_production_errors_rework_hold_and_andon_are_present():
    for token in (
        "冲压件出现起皱", "机器人漏焊一个焊点", "车门清漆出现流挂",
        "车轮扭矩低于规范", "前门间隙超差", "淋雨测试后车内进水",
        "返修", "隔离待判", "停线", "呼叫班组长", "原因分析",
        "ANDON · RED", "ANDON · YELLOW"
    ):
        assert token in JS
    assert "f2-andon" in CSS
    assert 'data-severity="red"' in CSS
    assert 'data-severity="yellow"' in CSS


def test_contextual_dialogues_and_language_modes_exist():
    for token in (
        "WORK DIALOGUE", "中文 + Pinyin", "English", "Mixed",
        "这件还能继续用吗？", "Can this panel continue to the next process?",
        "扭矩不合格，不能放行。", "Torque is out of specification; the vehicle cannot be released."
    ):
        assert token in JS


def test_factory_shift_supports_passenger_and_heavy_truck():
    assert "SHACMAN-class" in JS
    assert "vehicle:'car'" in JS
    assert "data-f2-vehicle=\"truck\"" in JS
    assert ".f2-product.truck" in CSS


def test_stage2_does_not_own_canonical_answers_xp_or_network():
    forbidden = (
        "submitAnswer(", "/api/games/", "fetch(", "spendable_xp", "awarded_xp",
        "MAX_GAME_ANSWERS =", "Three.", "three.js", "https://", "http://"
    )
    for token in forbidden:
        assert token not in JS
    assert "frontend.register('factory-simulator-stage2-v630'" in JS
    assert "No API, XP or canonical scoring ownership" in JS
