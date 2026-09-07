from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
LEARNING = (ROOT / 'static/frontend/learning.js').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = ['/frontend/app_state.js', '/frontend/learning.js', '/frontend/navigation.js']
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/learning.js') == 1

for token in (
    "Object.freeze(['home', 'topics', 'quiz', 'course30'])",
    "frontend.register('learning'",
    "event.stopImmediatePropagation()",
    "legacy().ensureChineseStandardBanner()",
    "state().set('view', target)",
    "api().request('/api/language/'",
    "'/terms?topic='",
    "'/quiz?topic='",
    "'/course30'",
    "'/api/course-day/result'",
    "legacy().submitPractice",
):
    assert token in LEARNING, token

for token in ('renderLearningHome','renderLearningTopics','renderLearningQuiz','renderLearningCourse30'):
    assert token not in LEARNING, token
    assert token not in BRIDGE, token

assert "frontend.get('learning').owns(view)" in NAV
assert "frontend.get('learning').navigate(view)" in NAV
assert "'learning'" in BOOT

# v6.0.16 physically removes superseded learning renderers from the shell.
for name in ('renderHome', 'renderTopics', 'renderQuiz', 'renderCourse30'):
    assert f'function {name}' not in APP, name
assert len(APP.encode('utf-8')) < 30_000

for script in ('learning.js','navigation.js','legacy_bridge.js'):
    subprocess.run(['node','--check',str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: learning owns home/topics/quiz/course30 and physical shell contains no learning renderers')
