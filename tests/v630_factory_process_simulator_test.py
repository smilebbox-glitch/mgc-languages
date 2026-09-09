from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "static/frontend/factory_process_simulator_v630.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/factory_process_simulator_v630.css").read_text(encoding="utf-8")


def test_simulator_assets_are_loaded():
    assert '/factory_process_simulator_v630.css' in INDEX
    assert '/frontend/factory_process_simulator_v630.js' in INDEX


def test_six_process_stages_and_eighteen_operations():
    for stage in ('stamping', 'welding', 'paint', 'assembly', 'quality', 'dealer'):
        assert f"id:'{stage}'" in JS
        assert f'data-stage="{stage}"' in CSS
    assert 'totalOperations:18' in JS
    assert '18 / 18' in JS


def test_chinese_english_and_mixed_learning_content():
    for token in (
        '冲压', 'chōngyā', '焊装', 'hànzhuāng', '涂装', 'túzhuāng',
        '总装', 'zǒngzhuāng', '质量与试验', '经销商交付',
        'Stamping', 'Body Welding', 'Paint Shop', 'Final Assembly',
        'Quality & Testing', 'Dealer Delivery', "language:'mixed'"
    ):
        assert token in JS


def test_user_performs_real_operations():
    for token in (
        '板料上料', '模具检查', '冲压成形', '夹具定位', '点焊', '焊点检查',
        '前处理', '电泳', '喷涂', '动力总成装配', '玻璃安装', '车轮拧紧',
        '间隙面差检查', '功能测试', '淋雨测试', '车辆接收', '交付前检查', '车辆交付'
    ):
        assert token in JS
    for visual in ('fps-press', 'fps-weld-robot', 'fps-paint', 'fps-hoist', 'fps-quality', 'fps-water', 'fps-dealer'):
        assert visual in CSS


def test_passenger_and_truck_tracks_are_supported():
    assert "vehicle==='truck'" in JS
    assert 'SHACMAN-class' in JS
    assert 'data-vehicle="truck"' in CSS


def test_special_game_does_not_modify_canonical_scoring_or_network():
    forbidden = (
        'submitAnswer(', '/api/games/', 'fetch(', 'spendable_xp', 'awarded_xp',
        'MAX_GAME_ANSWERS =', 'Three.', 'three.js', 'https://', 'http://'
    )
    for token in forbidden:
        assert token not in JS
    assert "frontend.register('factory-process-simulator-v630'" in JS
    assert 'SPECIAL GAME' in JS
