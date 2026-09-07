from __future__ import annotations

import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=(ROOT/'static/index.html').read_text(encoding='utf-8')
MODULE=(ROOT/'static/frontend/admin_ops.js').read_text(encoding='utf-8')
BOOT=(ROOT/'static/frontend/boot.js').read_text(encoding='utf-8')
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')

assets=['/frontend/content_governance.js','/frontend/admin_ops.js','/frontend/manager_admin.js','/frontend/navigation.js']
assert [INDEX.index(x) for x in assets] == sorted(INDEX.index(x) for x in assets)
assert INDEX.count('/frontend/admin_ops.js')==1
for token in (
    "frontend.register('admin-ops'", "if (user.role !== 'admin')", "function pilotGovernanceHTML()",
    "function bindPilotGovernance()", "'/api/admin/pilot/groups'", "'/members/'", "'/features/'", "'/assignments'",
    "method: 'PATCH'", "method: 'DELETE'", "method: 'PUT'", "Экспорт результатов CSV",
    "function bindITDashboard()", "'/api/admin/maintenance/cleanup?dry_run=true'",
    "'/api/admin/maintenance/cleanup?dry_run=false'", "'/api/admin/alerts/'", "'/ack'",
    "Acknowledged from IT dashboard", "frontend.get('error-boundary').record",
):
    assert token in MODULE, token
assert "'admin-ops'" in BOOT
for name in ('pilotGovernanceHTML','bindPilotGovernance','itDashboardHTML','bindITDashboard'):
    assert f'function {name}' not in APP, name
assert len(APP.encode('utf-8')) < 30_000
subprocess.run(['node','--check',str(ROOT/'static/frontend/admin_ops.js')],check=True,cwd=ROOT)
subprocess.run(['node','--check',str(ROOT/'static/app.js')],check=True,cwd=ROOT)
print('PASS: admin-ops owns pilot governance/IT mutations and physical shell contains no admin ops UI')
