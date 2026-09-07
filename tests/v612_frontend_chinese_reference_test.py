from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/chinese_reference.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')
DATA = json.loads((ROOT / 'data/chinese_foundations.json').read_text(encoding='utf-8'))

assets = [
    '/frontend/final_assessment.js',
    '/frontend/chinese_reference.js',
    '/frontend/content_governance.js',
    '/frontend/navigation.js',
]
positions = [INDEX.index(asset) for asset in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/chinese_reference.js') == 1

for token in (
    "const OWNED_VIEWS = Object.freeze(['chinese-basics'])",
    "frontend.register('chinese-reference'",
    "flags.chinese_reference !== false",
    "api().request('/api/chinese/foundations')",
    "state().set('chineseFoundations', data)",
    "legacy().newSessionId('tone-lab')",
    "legacy().submitPractice('tone_lab'",
    ".slice(0, 5)",
    "data-tone-choice",
    "Путунхуа (普通话)",
    "Диалекты ниже — только справка",
    "ОДИН СМЫСЛ · РАЗНЫЙ ЗВУК",
    "base.audio ? '<button",
    "event.stopImmediatePropagation()",
    "frontend.get('error-boundary').record",
):
    assert token in MODULE, token

assert "frontend.get('chinese-reference').navigate(view)" in NAV
assert "'chinese-reference'" in BOOT
assert "variant.audio" not in MODULE

standard = DATA.get('learning_standard') or {}
assert standard.get('name') == 'Путунхуа (普通话)'
assert 'основной китайский курс' in standard.get('primary_message', '').lower()
assert 'только справка' in standard.get('reference_message', '').lower()
putonghua = DATA.get('putonghua') or {}
assert len(putonghua.get('groups') or []) == 10
for comparison in putonghua.get('comparison_examples') or []:
    assert (comparison.get('standard') or {}).get('audio') is True
    for variant in comparison.get('variants') or []:
        assert not variant.get('audio'), variant

for legacy_name in ('toneLabStart', 'renderToneLabRound', 'renderChineseBasics'):
    assert f'function {legacy_name}' in APP
assert "'chinese-basics': renderChineseBasics" in APP
assert "'chinese-basics':'chinese_reference'" in APP
assert len(APP.encode('utf-8')) < 150_000

for script in ('chinese_reference.js', 'navigation.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.12 Chinese reference owns Putonghua foundations and Tone Lab while dialects remain reference-only')
