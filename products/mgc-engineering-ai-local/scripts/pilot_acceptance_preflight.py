#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(code, ok, detail): checks.append({"code":code,"pass":bool(ok),"detail":detail})
try:
    data=json.loads((ROOT/'pilot/golden_dataset_v1.json').read_text())
    check('golden_dataset_schema',data.get('schema')=='mgc-golden-automotive-dataset-v1',data.get('schema'))
    check('synthetic_never_go',data.get('synthetic_only') is True and data.get('authorizes_production_go') is False,'synthetic_only=true')
    check('golden_roles',set(data.get('expected_assertions',{}).get('required_roles',[]))=={'rd','manufacturing','quality'},'rd/manufacturing/quality')
except Exception as exc:
    check('golden_dataset',False,str(exc))
for rel in ['docs/CONTROLLED_AUTOMOTIVE_PILOT.md','docs/PILOT_KPI_DEFINITION.md','docs/PILOT_GO_NO_GO.md','backend/app/services/pilot_acceptance.py','backend/app/api/pilot_routes.py']:
    check('file:'+rel,(ROOT/rel).exists(),rel)
failed=[x for x in checks if not x['pass']]
print(json.dumps({"status":"PASS" if not failed else "FAIL","note":"Preflight validates the UAT harness only; it is not a real pilot GO decision.","checks":checks},indent=2))
sys.exit(1 if failed else 0)
