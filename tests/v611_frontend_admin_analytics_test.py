from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/admin_analytics.js').read_text(encoding='utf-8')
MANAGER = (ROOT / 'static/frontend/manager_admin.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = [
    '/frontend/content_governance.js',
    '/frontend/admin_ops.js',
    '/frontend/admin_analytics.js',
    '/frontend/manager_admin.js',
    '/frontend/navigation.js',
]
positions = [INDEX.index(asset) for asset in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/admin_analytics.js') == 1

for token in (
    "frontend.register('admin-analytics'",
    "user.role !== 'admin'",
    "api().request('/api/admin/analytics')",
    "api().request('/api/admin/users')",
    "api().request('/api/admin/taxonomy')",
    "api().request('/api/admin/terms')",
    "api().request('/api/admin/pilot-telemetry')",
    "api().request('/api/admin/it-dashboard')",
    "api().request('/api/admin/learning-error-telemetry')",
    "api().request('/api/admin/pilot/governance-summary')",
    "api().request('/api/admin/pilot/groups')",
    "api().request('/api/admin/pilot/features')",
    "api().request('/api/admin/learning/question-quality')",
    "'/api/admin/users/' + encodeURIComponent(id) + '/learning-stats'",
    "ops().pilotGovernanceHTML()",
    "ops().bindPilotGovernance()",
    "ops().bindITDashboard()",
    "content().questionQualityHTML(data.questionQuality)",
    "content().adminContentHTML()",
    "content().bindAdminContent()",
    "Slow-query fingerprints",
    "recovery_evidence",
    "maintenancePreview",
    "data-alert-ack",
    "Качество обучения · ошибки",
    "frontend.get('error-boundary').record",
):
    assert token in MODULE, token

assert "frontend.get('admin-analytics').renderAdmin()" in MANAGER
assert "return legacy().renderAdmin()" not in MANAGER
assert "frontend.get('content-governance').renderEditor()" in MANAGER
assert "'admin-analytics'" in BOOT

for legacy_name in ('renderAdmin', 'itDashboardHTML', 'learningErrorTelemetryHTML', 'openAdminUser'):
    assert f'function {legacy_name}' in APP
assert len(APP.encode('utf-8')) < 150_000

for script in ('admin_analytics.js', 'manager_admin.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.11 admin analytics owns full Admin orchestration, IT dashboard, telemetry and user detail')
