from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/admin_ops.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = [
    '/frontend/content_governance.js',
    '/frontend/admin_ops.js',
    '/frontend/manager_admin.js',
    '/frontend/navigation.js',
]
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/admin_ops.js') == 1

for token in (
    "frontend.register('admin-ops'",
    "if (user.role !== 'admin')",
    "function pilotGovernanceHTML()",
    "function bindPilotGovernance()",
    "'/api/admin/pilot/groups'",
    "'/members/'",
    "'/features/'",
    "'/assignments'",
    "method: 'PATCH'",
    "method: 'DELETE'",
    "method: 'PUT'",
    "Экспорт результатов CSV",
    "function bindITDashboard()",
    "'/api/admin/maintenance/cleanup?dry_run=true'",
    "'/api/admin/maintenance/cleanup?dry_run=false'",
    "'/api/admin/alerts/'",
    "'/ack'",
    "Acknowledged from IT dashboard",
    "root.pilotGovernanceHTML = pilotGovernanceHTML",
    "root.bindPilotGovernance = bindPilotGovernance",
    "root.itDashboardHTML = itDashboardHTML",
    "root.bindITDashboard = bindITDashboard",
    "legacyFallbacks: original",
    "frontend.get('error-boundary').record",
):
    assert token in MODULE, token

assert "original.itDashboardHTML(data)" in MODULE
assert "'admin-ops'" in BOOT

for name in ('pilotGovernanceHTML', 'bindPilotGovernance', 'itDashboardHTML', 'bindITDashboard'):
    assert f'function {name}' in APP
assert len(APP.encode('utf-8')) < 150_000

for script in ('admin_ops.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.10 admin ops owns pilot governance and IT mutations with admin-only staged renderer parity')
