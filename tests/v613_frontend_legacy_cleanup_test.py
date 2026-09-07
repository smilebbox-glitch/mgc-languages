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

retired = (
    'renderNotifications', 'saveNudgeSettings',
    'renderAssistant', 'askAssistant', 'renderKnowledge',
    'renderExam', 'startExam', 'answerExam',
    'renderManager', 'openManagerUser',
    'renderAdmin', 'itDashboardHTML', 'pilotGovernanceHTML', 'bindPilotGovernance',
    'learningErrorTelemetryHTML', 'bindITDashboard', 'questionQualityHTML',
    'adminTermCard', 'adminContentHTML', 'bindAdminContent', 'openAdminUser',
    'toneLabStart', 'renderToneLabRound', 'renderChineseBasics',
)
for name in retired:
    assert repr(name) in RETIRE, name
    assert f"root[name] = undefined" in RETIRE

# Remaining active legacy renderers are deliberately not retired yet.
for name in ('renderHome', 'renderTopics', 'renderQuiz', 'renderCourse30', 'renderRoleplay', 'renderGames', 'renderXP'):
    assert repr(name) not in RETIRE, name
    assert f"requireFunction('{name}'" in BRIDGE, name

# Admin/manager are no longer part of the allowed bridge surface.
assert "renderManager:" not in BRIDGE
assert "renderAdmin:" not in BRIDGE
assert "bridge.surface = Object.freeze(Object.keys(bridge))" in BRIDGE
assert "'legacy-retirement'" in BOOT
assert "frontend.register('legacy-retirement'" in RETIRE
assert "remainingBridgeSurface: frontend.get('legacy-app').surface" in RETIRE

# Historical declarations remain physically present for now; runtime exposure is what v6.0.13 retires.
for legacy_name in ('renderAdmin', 'renderManager', 'renderChineseBasics', 'renderExam', 'renderAssistant', 'renderNotifications'):
    assert f'function {legacy_name}' in APP

# Keep the monolith bounded while subsequent releases migrate learning/practice renderers.
assert len(APP.encode('utf-8')) < 150_000

# The bridge surface should be materially smaller than the pre-cleanup compatibility object.
bridge_keys = re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):', BRIDGE, flags=re.MULTILINE)
assert len(bridge_keys) <= 24, bridge_keys

for script in ('legacy_bridge.js', 'legacy_retirement.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.13 retires superseded legacy globals while preserving only learning/practice compatibility')
