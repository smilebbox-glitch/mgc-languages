from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEARNING=(ROOT/'static/frontend/learning.js').read_text(encoding='utf-8')
BRIDGE=(ROOT/'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE=(ROOT/'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
NAV=(ROOT/'static/frontend/navigation.js').read_text(encoding='utf-8')
INDEX=(ROOT/'static/index.html').read_text(encoding='utf-8')
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')

assert "Object.freeze(['home', 'topics', 'quiz', 'course30'])" in LEARNING
assert "frontend.register('learning'" in LEARNING
for name in ('renderHome','renderTopics','renderQuiz','renderCourse30','startQuiz','answerQuiz','buyQuizHelp','makePairOptions','answerPair','renderDayQuiz','answerDayQuiz'):
    assert f'function {name}' in LEARNING,name
    assert f'function {name}' not in APP,name
for token in ("'/terms?topic='","'/quiz?topic='","'/course30'","'/api/course-day/result'","'/api/gamification/spend'","legacy().submitPractice('quiz'","'course_day'","legacy().playPronunciation","legacy().ensureChineseStandardBanner()"):
    assert token in LEARNING,token
for token in ('pilotCohortHTML()','nudgeHTML()',"featureEnabled('xp_economy')",'МОЙ ПИЛОТНЫЙ ТРЕК','Ваш прогресс','Уровень обучения'):
    assert token in LEARNING,token
for token in ("closest('[data-language]')","closest('#pinyinToggle')","'/api/me/language'","'/api/learning/preferences'","await navigation().setView('home')","await navigation().setView(current().view || 'home')",'event.stopImmediatePropagation()'):
    assert token in LEARNING,token
for token in ('renderLearningHome','renderLearningTopics','renderLearningQuiz','renderLearningCourse30'):
    assert token not in LEARNING and token not in BRIDGE,token
for name in ('renderHome','renderTopics','renderQuiz','startQuiz','answerQuiz','buyQuizHelp','renderCourse30','makePairOptions','answerPair','renderDayQuiz','answerDayQuiz'):
    assert repr(name) in RETIRE,name
assert "frontend.get('learning').navigate(view)" in NAV
assert INDEX.index('/frontend/learning.js') < INDEX.index('/frontend/legacy_retirement.js') < INDEX.index('/frontend/navigation.js')
bridge_keys=re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):',BRIDGE,flags=re.MULTILINE)
assert len(bridge_keys)<=18,bridge_keys
assert len(APP.encode('utf-8'))<30_000
for path in (ROOT/'static/app.js',ROOT/'static/frontend/learning.js',ROOT/'static/frontend/legacy_bridge.js',ROOT/'static/frontend/legacy_retirement.js',ROOT/'static/frontend/navigation.js',ROOT/'static/frontend/boot.js'):
    subprocess.run(['node','--check',str(path)],check=True,cwd=ROOT)
print('PASS: core learning remains canonical after physical shell cleanup')
