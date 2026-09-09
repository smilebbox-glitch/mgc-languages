from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'static/frontend/animation_interaction_v630.js').read_text(encoding='utf-8')
CSS = (ROOT / 'static/animation_interaction_v630.css').read_text(encoding='utf-8')
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')


def require(text: str, needle: str, label: str) -> None:
    assert needle in text, f'missing {label}: {needle}'


def test_animation_interaction_assets_loaded():
    require(INDEX, '/animation_interaction_v630.css', 'animation interaction CSS')
    require(INDEX, '/frontend/animation_interaction_v630.js', 'animation interaction JS')


def test_interaction_stage_features_present():
    for needle, label in [
        ('Exploded View', 'exploded view'),
        ('Cutaway', 'cutaway'),
        ('Потоки', 'engine flow mode'),
        ('Инструменты: выкл', 'interactive tool mode'),
        ('3D Quality Inspector', 'quality inspector'),
        ('Диагностика 3D', 'powertrain diagnostics'),
        ('START-UP SEQUENCE', 'completion sequence'),
        ('QUALITY · PASS', 'quality pass state'),
        ('ai-camera-run', 'cinematic camera'),
        ('ai-install-rig', 'animated part installation'),
    ]:
        require(JS, needle, label)


def test_powertrain_cutaway_and_flows_are_animated():
    for needle, label in [
        ('ai-cutaway-layer', 'cutaway layer'),
        ('ai-cylinders', 'animated cylinders'),
        ('ai-crank', 'animated crankshaft'),
        ('高压燃油', 'heavy-diesel high-pressure fuel flow'),
        ('排气', 'exhaust flow'),
        ('空气', 'air flow'),
        ('@keyframes aiPiston', 'piston animation'),
        ('@keyframes aiCrank', 'crank animation'),
        ('@keyframes aiCamera', 'camera animation'),
    ]:
        require(JS + CSS, needle, label)


def test_quality_defects_cover_vehicle_interior_and_powertrain():
    for key in ('car:', 'truck:', 'carInterior:', 'truckInterior:', 'carEngine:', 'truckEngine:'):
        require(JS, key, f'defect catalog {key}')
    for term in ('车门间隙异常', '燃油箱固定异常', '安全带安装异常', '共轨压力异常', '涡轮增压器连接异常'):
        require(JS, term, f'Chinese defect learning term {term}')


def test_tool_learning_contains_chinese_pinyin_and_english():
    for term in ('扭矩扳手', 'niǔjǔ bānshǒu', 'torque wrench', '发动机装配台', 'piston ring compressor', 'fuel pressure tester'):
        require(JS, term, f'tool learning content {term}')


def test_architecture_boundary_preserved():
    banned = [
        'submitAnswer(',
        '/api/games/',
        'spendable_xp',
        'awarded_xp',
        'MAX_GAME_ANSWERS =',
        'fetch(',
    ]
    for token in banned:
        assert token not in JS, f'animation interaction addon must not own canonical contract: {token}'


def test_mobile_and_reduced_motion_present():
    require(CSS, '@media(max-width:760px)', 'mobile adaptation')
    require(CSS, '@media(prefers-reduced-motion:reduce)', 'reduced motion adaptation')
