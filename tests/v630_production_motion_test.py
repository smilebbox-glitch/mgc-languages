from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "static/frontend/production_motion_v630.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/production_motion_v630.css").read_text(encoding="utf-8")


def test_assets_are_loaded_after_factory_digital_thread():
    assert '/production_motion_v630.css' in INDEX
    assert '/frontend/production_motion_v630.js' in INDEX
    assert INDEX.index('/factory_digital_thread_v630.css') < INDEX.index('/production_motion_v630.css')
    assert INDEX.index('/frontend/factory_digital_thread_v630.js') < INDEX.index('/frontend/production_motion_v630.js')


def test_all_factory_motion_phases_exist():
    for phase in ('biw', 'paint', 'assembly', 'powertrain', 'interior', 'quality', 'release'):
        assert f"{phase}:{{" in JS
        assert f'data-motion-phase="{phase}"' in CSS


def test_production_equipment_and_motion_are_present():
    for token in (
        'fpm-robot', 'fpm-sparks', 'fpm-paint-rig', 'fpm-assembly-tool',
        'fpm-hoist', 'fpm-interior-carrier', 'fpm-quality-gantry',
        'fpm-release-gate', 'fpm-agv', 'fpmVehicleArrive'
    ):
        assert token in JS or token in CSS
    assert 'Проиграть доступный маршрут' in JS
    assert "unlocked:not(:disabled)" in JS


def test_learning_language_and_reduced_motion_contract():
    for token in ('焊装', 'hànzhuāng', '涂装', 'túzhuāng', '总装', 'zǒngzhuāng', '质量检查', 'zhìliàng jiǎnchá'):
        assert token in JS
    assert 'prefers-reduced-motion: reduce' in JS
    assert 'prefers-reduced-motion:reduce' in CSS


def test_layer_does_not_own_answers_scoring_xp_or_network():
    forbidden = (
        'submitAnswer(', '/api/games/', 'fetch(', 'spendable_xp', 'awarded_xp',
        'MAX_GAME_ANSWERS =', 'Three.', 'three.js', 'https://', 'http://'
    )
    for token in forbidden:
        assert token not in JS
    assert 'frontend.register(\'production-motion-v630\'' in JS
