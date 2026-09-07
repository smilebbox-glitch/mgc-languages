from __future__ import annotations

import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=(ROOT/'static/index.html').read_text(encoding='utf-8')
MODULE=(ROOT/'static/frontend/final_assessment.js').read_text(encoding='utf-8')
NAV=(ROOT/'static/frontend/navigation.js').read_text(encoding='utf-8')
BOOT=(ROOT/'static/frontend/boot.js').read_text(encoding='utf-8')
BRIDGE=(ROOT/'static/frontend/legacy_bridge.js').read_text(encoding='utf-8')
APP=(ROOT/'static/app.js').read_text(encoding='utf-8')

assets=['/frontend/assistant_knowledge.js','/frontend/final_assessment.js','/frontend/navigation.js']
assert [INDEX.index(x) for x in assets] == sorted(INDEX.index(x) for x in assets)
assert INDEX.count('/frontend/final_assessment.js')==1
for token in ("Object.freeze(['exam'])","frontend.register('final-assessment'","const EXAM_TOTAL = 50","const PASS_SCORE = 35","event.stopImmediatePropagation()","api().request('/api/language/' + encodeURIComponent(current.language) + '/final-exam')","api().request('/api/final-exam/result'","answers: []","legacy().submitPractice(","legacy().newSessionId('exam-' + latest.language)","'/summary'","state().set('summary', summary)","data-exam-answer=\"","Правильный ответ:","Завершить экзамен","frontend.get('error-boundary').record"):
    assert token in MODULE, token
assert "frontend.get('final-assessment').owns(view)" in NAV
assert "frontend.get('final-assessment').navigate(view)" in NAV
assert "'final-assessment'" in BOOT
assert "newSessionId: requireFunction('newSessionId', newSessionId)" in BRIDGE
assert "submitPractice: requireFunction('submitPractice', submitPractice)" in BRIDGE
for name in ('renderExam','startExam','answerExam'):
    assert f'function {name}' not in APP, name
assert len(APP.encode('utf-8')) < 30_000
for script in ('legacy_bridge.js','final_assessment.js','navigation.js','boot.js'):
    subprocess.run(['node','--check',str(ROOT/'static/frontend'/script)],check=True,cwd=ROOT)
subprocess.run(['node','--check',str(ROOT/'static/app.js')],check=True,cwd=ROOT)
print('PASS: final-assessment owns exam flow and physical shell contains no exam renderer')
