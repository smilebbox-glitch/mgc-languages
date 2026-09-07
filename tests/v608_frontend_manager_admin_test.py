from __future__ import annotations

import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=(ROOT/'static/index.html').read_text(encoding='utf-8')
MODULE=(ROOT/'static/frontend/manager_admin.js').read_text(encoding='utf-8')
BRIDGE=(ROOT/'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
NAV=(ROOT/'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT=(ROOT/'static/frontend/boot.js').read_text(encoding='utf-8')
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')

assets=['/frontend/final_assessment.js','/frontend/manager_admin.js','/frontend/navigation.js']
assert [INDEX.index(x) for x in assets] == sorted(INDEX.index(x) for x in assets)
assert INDEX.count('/frontend/manager_admin.js')==1
for token in (
    "Object.freeze(['manager', 'admin'])", "frontend.register('manager-admin'", "event.stopImmediatePropagation()",
    "role !== 'manager'", "!['admin', 'editor'].includes(role)", "Раздел доступен руководителю подразделения", "Недостаточно прав",
    "api().request('/api/manager/team')", "'/api/manager/team/' + encodeURIComponent(id) + '/learning-stats'",
    "state().set('managerTeam', team)", "frontend.get('content-governance').renderEditor()",
    "frontend.get('admin-analytics').renderAdmin()", "frontend.get('error-boundary').record",
):
    assert token in MODULE, token
for token in ('renderManager:','renderAdmin:'):
    assert token not in BRIDGE, token
assert "frontend.get('manager-admin').owns(view)" in NAV
assert "frontend.get('manager-admin').navigate(view)" in NAV
assert "'manager-admin'" in BOOT
for name in ('renderManager','renderAdmin','bindPilotGovernance','bindAdminContent','bindITDashboard'):
    assert f'function {name}' not in APP, name
assert len(APP.encode('utf-8')) < 30_000
for script in ('manager_admin.js','legacy_bridge.js','navigation.js','boot.js'):
    subprocess.run(['node','--check',str(ROOT/'static/frontend'/script)],check=True,cwd=ROOT)
subprocess.run(['node','--check',str(ROOT/'static/app.js')],check=True,cwd=ROOT)
print('PASS: manager/admin routing is fully modular and physical shell contains no management renderers')
