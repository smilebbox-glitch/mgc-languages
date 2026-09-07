from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')
BRIDGE=(ROOT/'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
RETIRE=(ROOT/'static/frontend/legacy_retirement.js').read_text(encoding='utf-8')
SESSION=(ROOT/'static/frontend/session_lifecycle.js').read_text(encoding='utf-8')

# Physical shell target: the old ~128 KB feature monolith is gone.
size=len(APP.encode('utf-8'))
assert size < 30_000, size
assert 'v6.0.16: physical frontend compatibility shell' in APP

required=(
    'boot','bindStaticEvents','configureAuthUi','setView','loadLanguage','showApp','showAuth','closeMenu',
    'ensureChineseStandardBanner','newSessionId','submitPractice','playPronunciation','setServiceStatus','toast','esc',
)
for name in required:
    assert f'function {name}' in APP,name
    assert f"requireFunction('{name}'" in BRIDGE,name

# Query primitives are arrow functions and remain part of the bridge.
assert 'const $ = ' in APP and 'const $$ = ' in APP
assert "query: requireFunction('$', $)" in BRIDGE
assert "queryAll: requireFunction('$$', $$)" in BRIDGE

for forbidden in (
    'renderView','renderHome','renderTopics','renderQuiz','renderCourse30','renderRoleplay','renderGames','renderXP',
    'renderNotifications','renderAssistant','renderKnowledge','renderExam','renderChineseBasics','renderManager','renderAdmin',
    'adminContentHTML','pilotGovernanceHTML','itDashboardHTML','learningErrorTelemetryHTML',
):
    assert f'function {forbidden}' not in APP,forbidden

# Feature navigation is delegated to modular owners; shell no longer binds feature navigation controls.
assert "function modularOwner(view)" in APP
for owner in ('learning','practice-games','support-notifications','assistant-knowledge','final-assessment','chinese-reference','manager-admin'):
    assert repr(owner) in APP,owner
assert "button.addEventListener('click', function () { setView(button.dataset.view); })" not in APP
assert "button.addEventListener('click', function () { switchLanguage(button.dataset.language); })" not in APP
assert "$('#pinyinToggle').addEventListener" not in APP

# Lifecycle compatibility remains deliberate until the shell itself is modularized.
assert "document.addEventListener('DOMContentLoaded', boot);" in APP
assert "document.removeEventListener('DOMContentLoaded', legacy.boot)" in SESSION

bridge_keys=re.findall(r'^\s{6}([A-Za-z][A-Za-z0-9]*):',BRIDGE,flags=re.MULTILINE)
assert len(bridge_keys)==18,bridge_keys
assert "bridge.surface = Object.freeze(Object.keys(bridge))" in BRIDGE

# Retirement stays as a guard for transitional global adapters created by modules.
assert "frontend.register('legacy-retirement'" in RETIRE
assert repr('practice-games') in RETIRE and repr('learning') in RETIRE

for path in (ROOT/'static/app.js',ROOT/'static/frontend/legacy_bridge.js',ROOT/'static/frontend/legacy_retirement.js',ROOT/'static/frontend/session_lifecycle.js'):
    subprocess.run(['node','--check',str(path)],check=True,cwd=ROOT)

print(f'PASS: v6.0.16 physical shell is {size} bytes with 18 shared bridge entries and zero feature renderers')
