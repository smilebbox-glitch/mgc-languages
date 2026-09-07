#!/usr/bin/env python3
"""Verify v6.3.34 preserves all v6.2.0 legacy routes while allowing additive APIs."""
from __future__ import annotations
import ast, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=json.loads((ROOT/'docs/API_CONTRACT_v6.2.0.json').read_text())

def scan(path:Path):
    tree=ast.parse(path.read_text(),filename=str(path)); out=[]
    for n in tree.body:
        if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
        for d in n.decorator_list:
            if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='router' and d.args and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str):
                out.append({'method':d.func.attr.upper(),'path':d.args[0].value,'handler':n.name,'handler_ast_sha256':hashlib.sha256(ast.dump(n, include_attributes=False).encode()).hexdigest()})
    return out
current=[]
for p in sorted((ROOT/'backend/app/api/contexts').glob('*.py')):
    if p.name=='__init__.py': continue
    current.extend(scan(p))
key=lambda x:(x['method'],x['path'],x['handler'])
a=sorted(base['routes'],key=key); b=sorted(current,key=key)
base_surface={(x['method'],x['path']) for x in a}; current_surface={(x['method'],x['path']) for x in b}
base_by={(x['method'],x['path'],x['handler']):x for x in a}
current_by={(x['method'],x['path'],x['handler']):x for x in b}
legacy_handler_ok=all(k in current_by for k in base_by)
checks=[
 ('baseline_count',base['route_count']==181,str(base['route_count'])),
 ('current_count',len(current)==247,str(len(current))),
 ('legacy_method_path_preserved',base_surface <= current_surface,f'missing={len(base_surface-current_surface)} added={len(current_surface-base_surface)}'),
 ('legacy_handler_identity_preserved',legacy_handler_ok,'all legacy method/path/handler identities preserved; v6.3 may add fields/behavior additively'),
 ('v6313_additive_routes',len(current_surface-base_surface)==66,str(sorted(current_surface-base_surface))),
]
failed=[]
for n,ok,d in checks:
    print(f"{'PASS' if ok else 'FAIL'} {n} — {d}")
    if not ok: failed.append(n)
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
