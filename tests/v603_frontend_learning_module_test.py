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
    "renderLearningHome",
    "renderLearningTopics",
    "renderLearningQuiz",
    "renderLearningCourse30",
):
    assert token in LEARNING, token

for token in (
    "renderLearningHome: requireFunction('renderHome', renderHome)",
    "renderLearningTopics: requireFunction('renderTopics', renderTopics)",
    "renderLearningQuiz: requireFunction('renderQuiz', renderQuiz)",
    "renderLearningCourse30: requireFunction('renderCourse30', renderCourse30)",
):
    assert token in BRIDGE, token

assert "frontend.get('learning').owns(view)" in NAV
assert "frontend.get('learning').navigate(view)" in NAV
assert "'learning'" in BOOT

# Historical renderers remain fallback-only during staged extraction.
for name in ('renderHome', 'renderTopics', 'renderQuiz', 'renderCourse30'):
    assert f'function {name}' in APP
assert len(APP.encode('utf-8')) < 150_000

subprocess.run(['node', '--check', str(ROOT / 'static/frontend/learning.js')], check=True, cwd=ROOT)
subprocess.run(['node', '--check', str(ROOT / 'static/frontend/navigation.js')], check=True, cwd=ROOT)
subprocess.run(['node', '--check', str(ROOT / 'static/frontend/legacy_bridge.js')], check=True, cwd=ROOT)

print('PASS: v6.0.3 learning module owns home/topics/quiz/course30 navigation with legacy renderers as staged fallback')
