from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/manager_admin.js').read_text(encoding='utf-8')
BRIDGE = (ROOT / 'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = [
    '/frontend/final_assessment.js',
    '/frontend/manager_admin.js',
    '/frontend/navigation.js',
]
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/manager_admin.js') == 1

for token in (
    "Object.freeze(['manager', 'admin'])",
    "frontend.register('manager-admin'",
    "event.stopImmediatePropagation()",
    "role !== 'manager'",
    "!['admin', 'editor'].includes(role)",
    "Раздел доступен руководителю подразделения",
    "Недостаточно прав",
    "api().request('/api/manager/team')",
    "'/api/manager/team/' + encodeURIComponent(id) + '/learning-stats'",
    "state().set('managerTeam', team)",
    "return legacy().renderAdmin()",
    "frontend.get('error-boundary').record",
):
    assert token in MODULE, token

assert "renderManager: requireFunction('renderManager', renderManager)" in BRIDGE
assert "renderAdmin: requireFunction('renderAdmin', renderAdmin)" in BRIDGE
assert "frontend.get('manager-admin').owns(view)" in NAV
assert "frontend.get('manager-admin').navigate(view)" in NAV
assert "'manager-admin'" in BOOT

for legacy_name in ('renderManager', 'renderAdmin', 'bindPilotGovernance', 'bindAdminContent', 'bindITDashboard'):
    assert f'function {legacy_name}' in APP, legacy_name

for endpoint in (
    '/api/admin/analytics',
    '/api/admin/users',
    '/api/admin/taxonomy',
    '/api/admin/terms',
    '/api/admin/pilot/governance-summary',
    '/api/admin/it-dashboard',
):
    assert endpoint in APP, endpoint

assert len(APP.encode('utf-8')) < 150_000

for script in ('manager_admin.js', 'legacy_bridge.js', 'navigation.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.8 manager-admin owns role-safe management routing with modular manager UI and staged admin compatibility')
