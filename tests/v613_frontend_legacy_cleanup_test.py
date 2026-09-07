from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE = (ROOT / 'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = [
    '/frontend/chinese_reference.js',
    '/frontend/content_governance.js',
    '/frontend/admin_ops.js',
    '/frontend/admin_analytics.js',
    '/frontend/manager_admin.js',
    '/frontend/legacy_retirement.js',
    '/frontend/navigation.js',
]
positions = [INDEX.index(asset) for asset in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/legacy_retirement.js') == 1

for owner in (
    'learning',
    'support-notifications',
    'assistant-knowledge',
    'final-assessment',
    'content-governance',
    'admin-ops',
    'admin-analytics',
    'manager-admin',
    'chinese-reference',
):
    assert repr(owner) in RETIRE, owner

previously_retired = (
    'renderNotifications', 'saveNudgeSettings',
    'renderAssistant', 'askAssistant', 'renderKnowledge',
    'renderExam', 'startExam', 'answerExam',
    'renderManager', 'openManagerUser',
    'renderAdmin', 'itDashboardHTML', 'pilotGovernanceHTML', 'bindPilotGovernance',
    'learningErrorTelemetryHTML', 'bindITDashboard', 'questionQualityHTML',
    'adminTermCard', 'adminContentHTML', 'bindAdminContent', 'openAdminUser',
    'toneLabStart', 'renderToneLabRound', 'renderChineseBasics',
)
for name in previously_retired:
    assert repr(name) in RETIRE, name

# Core learning is now also fully modular and retired from runtime exposure.
core_learning_retired = (
    'renderHome', 'renderTopics', 'renderQuiz', 'startQuiz', 'answerQuiz', 'buyQuizHelp',
    'renderCourse30', 'makePairOptions', 'answerPair', 'renderDayQuiz', 'answerDayQuiz',
)
for name in core_learning_retired:
    assert repr(name) in RETIRE, name
    assert f"requireFunction('{name}'" not in BRIDGE, name

# Practice remains the only feature renderer family still exposed by the bridge.
for name in ('renderRoleplay', 'renderGames', 'renderXP'):
    assert repr(name) not in RETIRE, name
    assert f"requireFunction('{name}'" in BRIDGE, name

assert "renderManager:" not in BRIDGE
assert "renderAdmin:" not in BRIDGE
assert "bridge.surface = Object.freeze(Object.keys(bridge))" in BRIDGE
assert "'legacy-retirement'" in BOOT
assert "frontend.register('legacy-retirement'" in RETIRE
assert "remainingBridgeSurface: frontend.get('legacy-app').surface" in RETIRE

# Historical declarations remain physically present for controlled rollback.
for legacy_name in (
    'renderHome', 'renderTopics', 'renderQuiz', 'renderCourse30',
    'renderAdmin', 'renderManager', 'renderChineseBasics', 'renderExam',
):
    assert f'function {legacy_name}' in APP

assert len(APP.encode('utf-8')) < 150_000

# The compatibility object contracts further after core learning extraction.
bridge_keys = re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):', BRIDGE, flags=re.MULTILINE)
assert len(bridge_keys) <= 21, bridge_keys

for script in ('legacy_bridge.js', 'legacy_retirement.js', 'learning.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: legacy cleanup now retires core learning while preserving practice compatibility')
