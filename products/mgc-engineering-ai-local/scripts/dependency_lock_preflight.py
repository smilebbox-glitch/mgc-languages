#!/usr/bin/env python3
from __future__ import annotations
import os, re, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
require=os.getenv('MGC_REQUIRE_LOCKFILES','false').lower()=='true' or os.getenv('MGC_REQUIRE_REPRODUCIBLE_BUILD','false').lower()=='true'
issues=[]; passes=[]

def hashed_lock(path:Path)->bool:
    if not path.exists(): return False
    text=path.read_text(encoding='utf-8')
    rows=[]; cur=''
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith('#'): continue
        cur += (' '+line if cur else line)
        if line.endswith('\\'):
            cur=cur[:-1].rstrip(); continue
        rows.append(cur); cur=''
    return bool(rows) and all('==' in x and '--hash=sha256:' in x for x in rows)

def wheelhouse_ok(profile:str)->bool:
    d=ROOT/f'backend/wheelhouse/{profile}'; m=d/'WHEELHOUSE_MANIFEST.json'
    if not m.exists(): return False
    try: data=json.loads(m.read_text())
    except Exception: return False
    for item in data.get('files') or []:
        p=d/item.get('name','')
        if not p.is_file(): return False
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item.get('sha256'): return False
    return bool(data.get('files'))

pl=ROOT/'frontend/package-lock.json'
if pl.exists():
    try:
        d=json.loads(pl.read_text()); ok=int(d.get('lockfileVersion',0))>=3
    except Exception: ok=False
    if ok: passes.append('frontend package-lock.json present and lockfileVersion>=3')
    else: issues.append('frontend/package-lock.json is invalid or too old')
else: issues.append('frontend/package-lock.json is absent')

for profile in ('core','ai','advanced'):
    lock=ROOT/f'backend/locks/requirements-{profile}.lock.txt'
    if hashed_lock(lock) and wheelhouse_ok(profile): passes.append(f'backend {profile} exact hashed lock + wheelhouse verified')
    else: issues.append(f'backend {profile} production lock/wheelhouse absent or unverified; generate on approved mirror')
for x in passes: print('PASS:',x)
if issues:
    for x in issues: print(('FAIL' if require else 'WARN')+': '+x)
    if require: raise SystemExit('Dependency lock gate failed')
else: print('PASS: dependency lock gate')
