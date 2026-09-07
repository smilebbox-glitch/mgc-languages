from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/support_notifications.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = ['/frontend/practice_games.js','/frontend/support_notifications.js','/frontend/navigation.js']
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/support_notifications.js') == 1

for token in (
    "Object.freeze(['notifications'])", "frontend.register('support-notifications'",
    "flags.learning_nudges !== false", "event.stopImmediatePropagation()",
    "api().request('/api/notifications/settings')", "api().request('/api/notifications/pending')",
    "'/api/notifications/' + encodeURIComponent(String(id)) + '/read'", "method: 'PUT'",
    "root.Notification.requestPermission()", "new root.Notification(item.title",
    "tag: 'mgc-learning-nudge'", "frontend.get('service-status').show",
    "frontend.get('error-boundary').record", "Эта функция пока не включена для вашей волны пилота",
):
    assert token in MODULE, token

assert "frontend.get('support-notifications').owns(view)" in NAV
assert "frontend.get('support-notifications').navigate(view)" in NAV
assert "'support-notifications'" in BOOT
assert 'function renderNotifications' not in APP
assert 'function saveNudgeSettings' not in APP
# Browser nudge dispatch remains a shared loadLanguage shell concern.
assert 'function maybeBrowserNudge' in APP
assert len(APP.encode('utf-8')) < 30_000

for script in ('support_notifications.js','navigation.js','boot.js','../app.js'):
    path = ROOT / 'static/frontend' / script if not script.startswith('../') else ROOT / 'static/app.js'
    subprocess.run(['node','--check',str(path)], check=True, cwd=ROOT)

print('PASS: support-notifications owns nudge UI/actions; shell retains only shared browser nudge dispatch')
