#!/usr/bin/env python3
"""Static verification for the v6.3.34 bounded-context route ownership."""
from __future__ import annotations
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
API=ROOT/'backend/app/api'
CONTEXTS=API/'contexts'
EXPECTED={
    'engineering_core':54,
    'configuration_change':53,
    'manufacturing_quality':53,
    'supplier_field':22,
    'intelligence_search':20,
    'platform_operations':45,
}

def routes(path:Path):
    tree=ast.parse(path.read_text(), filename=str(path))
    out=[]
    for n in tree.body:
        if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
        for d in n.decorator_list:
            if not (isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='router'): continue
            if d.args and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str):
                out.append((d.func.attr,d.args[0].value,n.name))
    return out

checks=[]
def check(name,ok,detail=''):
    checks.append((name,bool(ok),detail))

all_routes=[]
for name,count in EXPECTED.items():
    p=CONTEXTS/f'{name}.py'
    rs=routes(p) if p.exists() else []
    check(f'{name}.exists',p.exists(),str(p))
    check(f'{name}.route_count',len(rs)==count,f'{len(rs)}/{count}')
    all_routes += [(name,*r) for r in rs]

keys=[(method,path) for _,method,path,_ in all_routes]
check('route_total',len(all_routes)==247,str(len(all_routes)))
check('no_duplicate_method_path',len(keys)==len(set(keys)),str(len(keys)-len(set(keys))))
facade=(API/'routes.py').read_text()
check('facade_small',len(facade.splitlines())<=40,str(len(facade.splitlines())))
check('facade_has_no_handlers',not routes(API/'routes.py'))
shared=(API/'context_shared.py').read_text()
check('shared_route_free',not routes(API/'context_shared.py'))
check('shared_security_helpers',all(x in shared for x in ('def _allowed(', 'def _visible_docs(', 'def _get_visible_project(')))
main=(ROOT/'backend/app/main.py').read_text()
check('main_uses_context_registry','build_context_router(cfg.runtime_features)' in main)
registry=(API/'context_registry.py').read_text()
check('profile_aware_context_mount','active_bounded_contexts(features)' in registry)
manifest=(ROOT/'docs/API_BOUNDED_CONTEXTS_v6.3.34.md')
check('ownership_manifest',manifest.exists() and all(f'## {name}' in manifest.read_text() for name in EXPECTED))

failed=[x for x in checks if not x[1]]
for name,ok,detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}"+(f' — {detail}' if detail else ''))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
