from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PT = (ROOT / 'static/frontend/powertrain_builder_v630.js').read_text(encoding='utf-8')
OPS = (ROOT / 'static/frontend/assembly_operations_v630.js').read_text(encoding='utf-8')
PTCSS = (ROOT / 'static/powertrain_builder_v630.css').read_text(encoding='utf-8')
OPSCSS = (ROOT / 'static/assembly_operations_v630.css').read_text(encoding='utf-8')
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')


def block_between(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def count_catalog_entries(block: str) -> int:
    return len(re.findall(r"\b[a-z_]+:\['", block))


def test_assets_loaded():
    for token in [
        '/powertrain_builder_v630.css', '/assembly_operations_v630.css',
        '/frontend/powertrain_builder_v630.js', '/frontend/assembly_operations_v630.js',
    ]:
        assert token in INDEX
    assert "frontend.register('powertrain-builder-v630'" in PT
    assert "frontend.register('assembly-operations-v630'" in OPS


def test_two_engine_modes_and_node_counts():
    assert count_catalog_entries(block_between(PT, 'const CAR_ENGINE={', '};\n  const TRUCK_ENGINE=')) == 14
    assert count_catalog_entries(block_between(PT, 'const TRUCK_ENGINE={', '};\n  const MODES=')) == 15
    assert 'Собери двигатель легкового автомобиля' in PT
    assert 'Собери двигатель грузовика' in PT


def test_ten_ready_tasks_per_engine():
    for mode in ['carEngine', 'truckEngine']:
        match = re.search(rf"{mode}:\{{[^\n]+taskIds:\[([^\]]+)\]", PT)
        assert match, mode
        ids = re.findall(r"'([^']+)'", match.group(1))
        assert len(ids) == 10, (mode, ids)
        assert len(ids) == len(set(ids))
    assert "TASKS[mode]=MODES[mode].taskIds.map" in PT


def test_powertrain_learning_languages():
    for token in [
        '缸体', 'gāngtǐ', '曲轴', 'qūzhóu', '涡轮增压器', 'wōlún zēngyāqì',
        '共轨', 'gòngguǐ', '飞轮', 'fēilún',
        'data-pt-lang="chinese"', 'data-pt-lang="english"', 'data-pt-lang="mixed"',
        "session.language==='mixed'", 'phraseEn', 'phraseZh', 'phrasePy',
    ]:
        assert token in PT


def test_real_webgl_progressive_engine_and_running_state():
    for token in [
        "getContext('webgl'", 'pointerdown', 'pointermove', 'pt3d-marker',
        'if(step>this.completed&&!this.complete)return',
        "part[5]==='crank'", "part[5]==='piston'", 'requestAnimationFrame',
        'ENGINE RUNNING', 'RPM', 'AudioContext', 'Двигатель запущен', 'Дизельный двигатель запущен',
    ]:
        assert token in PT
    assert 'touch-action:none' in PTCSS
    assert '@media(prefers-reduced-motion:reduce)' in PTCSS


def test_assembly_operation_motion_and_quality_inspection():
    for token in [
        'QUALITY INSPECTION', 'Контроль качества', '5 из 5 контрольных точек',
        'QUALITY · PASS', 'Позиционирование → фиксация → подтверждение',
        'front_door', 'fuel_tank', 'seatbelt', 'parking_brake',
        'abopPartIn', 'abopToolIn', 'abopLock',
    ]:
        assert token in OPS or token in OPSCSS
    assert len(re.findall(r"\['(?:front_door|cab_door|seat|driver_seat)'", OPS)) >= 4


def test_new_layers_do_not_own_api_xp_or_canonical_scoring():
    forbidden = [
        '/api/games/', 'submitAnswer(', 'submitPractice(', 'awarded_xp',
        'spendable_xp', 'fetch(', 'MAX_GAME_ANSWERS',
    ]
    for token in forbidden:
        assert token not in PT, token
        assert token not in OPS, token
    assert 'No API, XP or canonical game scoring ownership' in PT
    assert 'No API, XP or canonical scoring ownership' in OPS


def test_no_external_assets_or_cdn():
    lower = (PT + OPS + PTCSS + OPSCSS).lower()
    for token in ['https://', 'http://', 'three.js', 'unpkg.com', 'cdn.jsdelivr.net']:
        assert token not in lower, token
