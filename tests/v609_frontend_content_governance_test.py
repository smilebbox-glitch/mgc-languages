from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/content_governance.js').read_text(encoding='utf-8')
MANAGER = (ROOT / 'static/frontend/manager_admin.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = [
    '/frontend/final_assessment.js',
    '/frontend/content_governance.js',
    '/frontend/manager_admin.js',
    '/frontend/navigation.js',
]
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/content_governance.js') == 1

for token in (
    "frontend.register('content-governance'",
    "['admin', 'editor'].includes(user.role)",
    "api().request('/api/admin/taxonomy')",
    "api().request('/api/admin/terms')",
    "api().request('/api/admin/learning/question-quality')",
    "api().request('/api/admin/terms', {method: 'POST'",
    "new FormData()",
    "'/api/admin/terms/import?default_language='",
    "'/submit-review'",
    "'/approve'",
    "'/reject'",
    "'/revisions'",
    "role === 'admin' && item.status === 'review'",
    "root.adminContentHTML = adminContentHTML",
    "root.bindAdminContent = bindAdminContent",
    "root.adminTermCard = adminTermCard",
    "root.questionQualityHTML = questionQualityHTML",
    "legacyFallbacks: original",
    "frontend.get('error-boundary').record",
):
    assert token in MODULE, token

assert "user.role === 'editor'" in MANAGER
assert "frontend.get('content-governance').renderEditor()" in MANAGER
assert "return legacy().renderAdmin()" in MANAGER
assert "'content-governance'" in BOOT

for name in ('adminContentHTML', 'bindAdminContent', 'adminTermCard', 'questionQualityHTML'):
    assert f'function {name}' in APP
assert len(APP.encode('utf-8')) < 150_000

for script in ('content_governance.js', 'manager_admin.js', 'boot.js'):
    subprocess.run(['node', '--check', str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)

print('PASS: v6.0.9 content governance owns terminology workflow with editor/admin parity and staged legacy adapters')
