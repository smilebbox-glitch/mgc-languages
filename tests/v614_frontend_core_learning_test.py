from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNING = (ROOT / 'static/frontend/learning.js').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE = (ROOT / 'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assert "Object.freeze(['home', 'topics', 'quiz', 'course30'])" in LEARNING
assert "frontend.register('learning'" in LEARNING

for function_name in (
    'renderHome', 'renderTopics', 'renderQuiz', 'renderCourse30',
    'startQuiz', 'answerQuiz', 'buyQuizHelp',
    'makePairOptions', 'answerPair', 'renderDayQuiz', 'answerDayQuiz',
):
    assert f'function {function_name}' in LEARNING, function_name

for token in (
    "'/terms?topic='", "'/quiz?topic='", "'/course30'", "'/api/course-day/result'",
    "'/api/gamification/spend'", "legacy().submitPractice('quiz'",
    "legacy().submitPractice(\n      'pair'", "'course_day'",
    "legacy().playPronunciation", "legacy().ensureChineseStandardBanner()",
):
    assert token in LEARNING, token

for token in (
    'pilotCohortHTML()', 'nudgeHTML()', "featureEnabled('xp_economy')",
    'МОЙ ПИЛОТНЫЙ ТРЕК', 'Ваш прогресс', 'Уровень обучения',
):
    assert token in LEARNING, token

for token in (
    "closest('[data-language]')", "closest('#pinyinToggle')",
    "'/api/me/language'", "'/api/learning/preferences'",
    "await navigation().setView('home')", "await navigation().setView(current().view || 'home')",
    'event.stopImmediatePropagation()',
):
    assert token in LEARNING, token

for token in (
    'renderLearningHome', 'renderLearningTopics', 'renderLearningQuiz', 'renderLearningCourse30',
):
    assert token not in LEARNING, token
    assert token not in BRIDGE, token

# Shared practice/audio primitives remain shell contracts, but practice renderers are now modular too.
assert "playPronunciation: requireFunction('playPronunciation', playPronunciation)" in BRIDGE
assert "submitPractice: requireFunction('submitPractice', submitPractice)" in BRIDGE
for token in ('renderPracticeRoleplay', 'renderPracticeGames', 'renderPracticeXP'):
    assert token not in BRIDGE, token

assert repr('learning') in RETIRE
assert repr('practice-games') in RETIRE
for name in (
    'renderHome', 'renderTopics', 'renderQuiz', 'startQuiz', 'answerQuiz', 'buyQuizHelp',
    'renderCourse30', 'makePairOptions', 'answerPair', 'renderDayQuiz', 'answerDayQuiz',
):
    assert repr(name) in RETIRE, name

for name in ('renderHome', 'renderTopics', 'renderQuiz', 'renderCourse30'):
    assert f'function {name}' in APP, name
assert "frontend.get('learning').navigate(view)" in NAV
assert INDEX.index('/frontend/learning.js') < INDEX.index('/frontend/practice_games.js')
assert INDEX.index('/frontend/practice_games.js') < INDEX.index('/frontend/legacy_retirement.js')
assert INDEX.index('/frontend/legacy_retirement.js') < INDEX.index('/frontend/navigation.js')

bridge_keys = re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):', BRIDGE, flags=re.MULTILINE)
assert len(bridge_keys) <= 18, bridge_keys
assert len(APP.encode('utf-8')) < 150_000

for script in ('learning.js', 'practice_games.js', 'legacy_bridge.js', 'legacy_retirement.js', 'navigation.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.14 core learning remains canonical after practice extraction')
