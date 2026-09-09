from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'static/frontend/assembly_builder_v630.js').read_text(encoding='utf-8')
FEEDBACK_JS = (ROOT / 'static/frontend/assembly_builder_language_feedback_v630.js').read_text(encoding='utf-8')
CSS = (ROOT / 'static/assembly_builder_v630.css').read_text(encoding='utf-8')
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')


def block_between(start: str, end: str) -> str:
    return JS.split(start, 1)[1].split(end, 1)[0]


def count_catalog_entries(block: str) -> int:
    return len(re.findall(r"\b[a-z_]+:\['", block))


def task_ids(mode: str):
    match = re.search(rf"{mode}:\{{[^\n]+taskIds:\[([^\]]+)\]", JS)
    assert match, f'missing taskIds for {mode}'
    return re.findall(r"'([^']+)'", match.group(1))


def test_assets_loaded():
    assert '/assembly_builder_v630.css' in INDEX
    assert '/frontend/assembly_builder_v630.js' in INDEX
    assert '/frontend/assembly_builder_language_feedback_v630.js' in INDEX
    assert "frontend.register('assembly-builder-v630'" in JS
    assert "frontend.register('assembly-builder-language-feedback-v630'" in FEEDBACK_JS


def test_four_builder_modes_and_node_counts():
    assert count_catalog_entries(block_between('const CAR_EXT={', '};\n  const TRUCK_EXT=')) == 16
    assert count_catalog_entries(block_between('const TRUCK_EXT={', '};\n  const CAR_INT=')) == 18
    assert count_catalog_entries(block_between('const CAR_INT={', '};\n  const TRUCK_INT=')) == 16
    assert count_catalog_entries(block_between('const TRUCK_INT={', '};\n\n  const MODES=')) == 15
    for title in ['Собери автомобиль', 'Собери грузовик', 'Собери салон', 'Собери кабину грузовика']:
        assert title in JS


def test_ten_ready_tasks_per_mode():
    for mode in ['car', 'truck', 'carInterior', 'truckInterior']:
        ids = task_ids(mode)
        assert len(ids) == 10, (mode, ids)
        assert len(ids) == len(set(ids)), mode
    assert "TASKS[mode]=MODES[mode].taskIds.map" in JS


def test_learning_languages_and_pinyin():
    for token in [
        '前保险杠', 'qián bǎoxiǎnggàng',
        '驾驶室', 'jiàshǐshì',
        '方向盘', 'fāngxiàngpán',
        '卧铺', 'wòpù',
        "data-ab-lang=\"chinese\"", "data-ab-lang=\"english\"", "data-ab-lang=\"mixed\"",
    ]:
        assert token in JS
    assert "session.language==='mixed'" in JS
    assert 'Подсказки интерфейса остаются на русском' in JS


def test_success_feedback_follows_learning_language():
    for token in [
        "if(value==='mixed')return index%2===0?'chinese':'english'",
        'task.phraseEn', 'task.phraseZh', 'task.phrasePy', 'task.phraseRu',
        "status.textContent.indexOf('Верно.')",
    ]:
        assert token in FEEDBACK_JS
    forbidden = ['/api/games/', 'submitAnswer(', 'submitPractice(', 'fetch(']
    for token in forbidden:
        assert token not in FEEDBACK_JS


def test_real_webgl_interaction_and_progressive_assembly():
    for token in [
        "getContext('webgl'", 'pointerdown', 'pointermove',
        'ab3d-marker', 'setCompleted', 'setCurrent', 'setComplete',
        "if(step>this.completed&&!this.complete)return",
    ]:
        assert token in JS
    assert 'touch-action:none' in CSS
    assert '@media(prefers-reduced-motion:reduce)' in CSS


def test_completion_reward_engine_start():
    for token in [
        'AudioContext', 'startSound()', 'ENGINE START',
        'Автомобиль собран', 'Грузовик готов к работе',
        'Салон собран', 'Кабина готова',
        'Фары включены, двигатель запущен',
        '10 из 10 заданий выполнены успешно',
    ]:
        assert token in JS or token in CSS


def test_builder_does_not_own_api_xp_or_canonical_scoring():
    forbidden = [
        '/api/games/', 'submitAnswer(', 'submitPractice(',
        'awarded_xp', 'spendable_xp', 'fetch(',
    ]
    for token in forbidden:
        assert token not in JS, token
    assert 'No API, XP or canonical game scoring ownership' in JS


def test_no_external_assets_or_cdn():
    lower = (JS + FEEDBACK_JS + CSS).lower()
    for token in ['https://', 'http://', 'three.js', 'unpkg.com', 'cdn.jsdelivr.net']:
        assert token not in lower, token
