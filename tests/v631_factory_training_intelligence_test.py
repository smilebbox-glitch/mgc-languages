from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = (ROOT / "static/frontend/boot.js").read_text(encoding="utf-8")
JS = (ROOT / "static/frontend/factory_training_intelligence_v631.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/factory_training_intelligence_v631.css").read_text(encoding="utf-8")


def test_v631_assets_are_loaded_from_optional_boot_layer():
    assert "/factory_training_intelligence_v631.css" in BOOT
    assert "/frontend/factory_training_intelligence_v631.js" in BOOT
    assert "loadProductionSimulationEnhancements" in BOOT


def test_linked_consequences_cross_factory_stages():
    for stage in ("stamping", "welding", "paint", "assembly", "quality", "dealer"):
        assert stage in JS
    for token in (
        "CONSEQUENCES", "session.latent", "minStage", "Production Thread",
        "Дефект пропущен дальше", "Проявилось отложенное последствие"
    ):
        assert token in JS


def test_training_kpis_and_chinese_terms_exist():
    for token in (
        "FPY (сим.)", "一次合格率", "yīcì hégé lǜ",
        "返修", "fǎnxiū", "停机时间", "tíngjī shíjiān",
        "质量隔离", "zhìliàng gélí", "节拍时间", "jiépāi shíjiān",
        "周期时间", "zhōuqī shíjiān", "Cycle / Takt"
    ):
        assert token in JS


def test_shift_report_and_adaptive_next_shift_exist():
    for token in (
        "SHIFT REPORT · FACTORY TRAINING INTELLIGENCE", "Отчёт смены",
        "точность решений", "Critical escapes", "Следующая смена",
        "weightedEvents", "stageMisses", "termMisses", "PROFILE_KEY",
        "Адаптивная следующая смена"
    ):
        assert token in JS


def test_voice_dialogues_support_chinese_english_and_slow_mode():
    for token in (
        "speechSynthesis", "SpeechSynthesisUtterance", "zh-CN", "en-US",
        "普通话 · PUTONGHUA", "Озвучить", "Медленно", "autoVoice"
    ):
        assert token in JS


def test_factory_roles_and_vehicle_tracks_are_reused():
    assert "factory-simulator-stage2-v630" in JS
    assert "data-fti-vehicle=\"car\"" in JS
    assert "data-fti-vehicle=\"truck\"" in JS
    assert "SHACMAN-class reference" in JS
    assert "Operator / Engineer / Team Leader" in JS


def test_v631_is_local_and_does_not_own_canonical_scoring_or_xp():
    forbidden = (
        "submitAnswer(", "/api/games/", "fetch(", "spendable_xp", "awarded_xp",
        "MAX_GAME_ANSWERS =", "Three.", "three.js", "https://", "http://"
    )
    for token in forbidden:
        assert token not in JS
    assert "No API, XP or canonical scoring ownership" in JS
    assert "frontend.register('factory-training-intelligence-v631'" in JS


def test_v631_layout_is_responsive_and_reduced_motion_safe():
    for token in (
        ".fti-kpis", ".fti-report-grid", ".fti-event-grid",
        "@media(max-width:960px)", "@media(max-width:560px)",
        "@media(prefers-reduced-motion:reduce)"
    ):
        assert token in CSS
