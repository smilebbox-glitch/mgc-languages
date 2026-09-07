#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(code, ok, detail): checks.append((code,bool(ok),detail))
svc=(ROOT/'backend/app/services/ux_simplification.py').read_text()
ui=(ROOT/'frontend/src/main.tsx').read_text()
pilot=(ROOT/'backend/app/services/pilot_acceptance.py').read_text()
check('ux.bounded-actions','MAX_PRIMARY_ACTIONS = 5' in svc,'max primary actions = 5')
check('ux.bounded-decisions','MAX_DECISIONS = 3' in svc,'max decisions = 3')
check('ux.bounded-guides','MAX_GUIDED_WORKFLOWS = 3' in svc,'max guided workflows = 3')
check('ux.progressive-disclosure','drilldown_collapsed_by_default' in svc and 'projectDrilldown' in ui,'specialist modules collapsed by default')
check('ux.role-not-auth','role_is_ui_focus_not_authorization' in svc,'role is presentation only')
check('ux.critical-pilot-gate','critical_usability_issues' in pilot,'critical UX issue blocks controlled GO')
check('ux.high-pilot-gate','high_usability_issues' in pilot,'high UX issue is conditional gate')
check('ux.feedback-runbook',(ROOT/'docs/UX_SIMPLIFICATION_AND_FEEDBACK_CLOSURE.md').exists(),'feedback closure runbook present')
check('ux.role-guides',(ROOT/'docs/ROLE_GUIDED_WORKFLOWS.md').exists(),'role guided workflow doc present')
failed=[x for x in checks if not x[1]]
print('UX acceptance preflight')
for code,ok,detail in checks: print(('PASS' if ok else 'FAIL'),code,'—',detail)
print(f"PASS: {len(checks)-len(failed)}/{len(checks)} checks" if not failed else f"FAIL: {len(failed)} failures")
sys.exit(1 if failed else 0)
