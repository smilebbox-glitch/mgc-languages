from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'static/frontend/factory_digital_thread_v630.js'
CSS = ROOT / 'static/factory_digital_thread_v630.css'
INDEX = ROOT / 'static/index.html'


def require(text: str, token: str):
    assert token in text, f'missing required token: {token}'


def test_factory_digital_thread_contract():
    js = JS.read_text(encoding='utf-8')
    css = CSS.read_text(encoding='utf-8')
    index = INDEX.read_text(encoding='utf-8')

    require(js, "frontend.register('factory-digital-thread-v630'")
    for stage in ('biw', 'paint', 'assembly', 'powertrain', 'interior', 'quality', 'release'):
        require(js, f"id:'{stage}'")

    require(js, "vehicle==='truck'?'truck':'car'")
    require(js, "assembly-builder-v630")
    require(js, "powertrain-builder-v630")
    require(js, "game-lab-v618")
    require(js, "truckEngine")
    require(js, "truckInterior")
    require(js, "SHACMAN-class")

    for term in ('白车身', '涂装', '总装', '发动机', '仪表板', '间隙', '下线', '共轨', '涡轮增压器', '卧铺'):
        require(js, term)

    for forbidden in ('submitAnswer(', '/api/games/', 'spendable_xp', 'awarded_xp', 'MAX_GAME_ANSWERS =', 'fetch('):
        assert forbidden not in js, f'forbidden canonical ownership token: {forbidden}'

    require(css, '.factory-digital-thread-v630')
    require(css, '[data-phase="biw"]')
    require(css, '[data-phase="quality"]')
    require(css, '@media(prefers-reduced-motion:reduce)')

    require(index, '/factory_digital_thread_v630.css')
    require(index, '/frontend/factory_digital_thread_v630.js')


def test_thread_has_local_geometry_for_both_vehicle_classes():
    js = JS.read_text(encoding='utf-8')
    require(js, 'function carGeometry()')
    require(js, 'function truckGeometry()')
    require(js, 'ProductionTwin3D')
    require(js, "powerPreference:'low-power'")
    assert 'three.js' not in js.lower()
    assert 'cdn' not in js.lower().replace('no cdn', '')
