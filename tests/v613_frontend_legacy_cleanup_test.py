from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=(ROOT/'static/index.html').read_text(encoding='utf-8')
BRIDGE=(ROOT/'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE=(ROOT/'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
BOOT=(ROOT/'static/frontend/boot.js').read_text(encoding='utf-8')
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')

assets=['/frontend/learning.js','/frontend/practice_games.js','/frontend/chinese_reference.js','/frontend/content_governance.js','/frontend/admin_ops.js','/frontend/admin_analytics.js','/frontend/manager_admin.js','/frontend/legacy_retirement.js','/frontend/navigation.js']
positions=[INDEX.index(x) for x in assets]
assert positions==sorted(positions),positions
assert INDEX.count('/frontend/legacy_retirement.js')==1

for owner in ('learning','practice-games','support-notifications','assistant-knowledge','final-assessment','content-governance','admin-ops','admin-analytics','manager-admin','chinese-reference'):
    assert repr(owner) in RETIRE, owner

retired=(
    'renderHome','renderTopics','renderQuiz','startQuiz','answerQuiz','buyQuizHelp','renderCourse30','makePairOptions','answerPair','renderDayQuiz','answerDayQuiz',
    'scenarioProgressKey','getScenarioProgress','saveScenarioProgress','renderRoleplay','answerScenario','renderGames','startGame','renderXP','renderXpPack','buyReward','xpPanelHTML','refreshGamification',
    'renderNotifications','saveNudgeSettings','renderAssistant','askAssistant','renderKnowledge','renderExam','startExam','answerExam',
    'renderManager','openManagerUser','renderAdmin','itDashboardHTML','pilotGovernanceHTML','bindPilotGovernance','learningErrorTelemetryHTML','bindITDashboard','questionQualityHTML','adminTermCard','adminContentHTML','bindAdminContent','openAdminUser','toneLabStart','renderToneLabRound','renderChineseBasics',
)
for name in retired:
    assert repr(name) in RETIRE, name
    assert f'function {name}' not in APP, name

for required in ('boot','bindStaticEvents','configureAuthUi','setView','loadLanguage','showApp','showAuth','closeMenu','ensureChineseStandardBanner','newSessionId','submitPractice','playPronunciation','setServiceStatus','toast','esc'):
    assert f"requireFunction('{required}'" in BRIDGE, required
assert "bridge.surface = Object.freeze(Object.keys(bridge))" in BRIDGE
bridge_keys=re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):',BRIDGE,flags=re.MULTILINE)
assert len(bridge_keys)<=18,bridge_keys
assert len(APP.encode('utf-8'))<30_000
assert "frontend.register('legacy-retirement'" in RETIRE
assert "'legacy-retirement'" in BOOT

for path in (ROOT/'static/app.js',ROOT/'static/frontend/legacy_bridge.js',ROOT/'static/frontend/legacy_retirement.js',ROOT/'static/frontend/learning.js',ROOT/'static/frontend/practice_games.js',ROOT/'static/frontend/boot.js'):
    subprocess.run(['node','--check',str(path)],check=True,cwd=ROOT)
print('PASS: legacy retirement guards a physical shell with no feature renderer implementations')
