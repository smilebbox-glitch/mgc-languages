from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / 'static/index.html').read_text(encoding='utf-8')
MODULE = (ROOT / 'static/frontend/assistant_knowledge.js').read_text(encoding='utf-8')
NAV = (ROOT / 'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT = (ROOT / 'static/frontend/boot.js').read_text(encoding='utf-8')
APP = (ROOT / 'static/app.js').read_text(encoding='utf-8')

assets = ['/frontend/support_notifications.js','/frontend/assistant_knowledge.js','/frontend/navigation.js']
positions = [INDEX.index(x) for x in assets]
assert positions == sorted(positions), positions
assert INDEX.count('/frontend/assistant_knowledge.js') == 1

for token in (
    "Object.freeze(['assistant', 'knowledge'])", "frontend.register('assistant-knowledge'",
    "flags.ai_assistant !== false", "event.stopImmediatePropagation()",
    "api().request('/api/assistant'", "api().request('/api/knowledge?language=' + encodeURIComponent(current.language))",
    "body: JSON.stringify({language: current.language, question: question})",
    "data-go=\"roleplay\"", "data-speak-text=\"", "function termCard(item)",
    "state().set('knowledgeItems', items)", "state().set('knowledgeTopic'", "state().set('knowledgeId'",
    "frontend.get('error-boundary').record", "Эта функция пока не включена для вашей волны пилота",
):
    assert token in MODULE, token

assert "frontend.get('assistant-knowledge').owns(view)" in NAV
assert "frontend.get('assistant-knowledge').navigate(view)" in NAV
assert "'assistant-knowledge'" in BOOT
for name in ('renderAssistant','askAssistant','renderKnowledge','termCard'):
    assert f'function {name}' not in APP, name
assert len(APP.encode('utf-8')) < 30_000

for script in ('assistant_knowledge.js','navigation.js','boot.js'):
    subprocess.run(['node','--check',str(ROOT / 'static/frontend' / script)], check=True, cwd=ROOT)
subprocess.run(['node','--check',str(ROOT / 'static/app.js')], check=True, cwd=ROOT)

print('PASS: assistant-knowledge owns AI/knowledge UI and physical shell contains no assistant renderers')
