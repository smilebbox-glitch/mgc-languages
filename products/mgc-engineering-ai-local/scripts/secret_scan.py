#!/usr/bin/env python3
from __future__ import annotations
import math, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','models','storage','backups','node_modules','dist','.pytest_cache','__pycache__'}
TEXT_EXT={'.py','.sh','.yml','.yaml','.json','.md','.txt','.toml','.ini','.conf','.template','.example','.ts','.tsx','.js','.html','.env'}
PEM=re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
TOKENS=[re.compile(r'AKIA[0-9A-Z]{16}'),re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(r'xox[baprs]-[A-Za-z0-9-]{20,}')]
ASSIGN=re.compile(r'(?i)(password|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*["\']([^"\']+)["\']')
ALLOW=('change-me','replace-me','replace-with','local-only','example','dummy','test-secret','redacted','${','set ')
def entropy(s):
    if not s:return 0
    return -sum((s.count(c)/len(s))*math.log2(s.count(c)/len(s)) for c in set(s))
issues=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or any(x in EXCLUDE for x in p.parts): continue
    if p.suffix.lower() not in TEXT_EXT and p.name not in {'.env','.env.example'}: continue
    try: txt=p.read_text(errors='ignore')
    except Exception: continue
    if PEM.search(txt): issues.append((p,0,'private-key-material'))
    for rx in TOKENS:
        for m in rx.finditer(txt): issues.append((p,txt.count('\n',0,m.start())+1,'known-token-pattern'))
    if p.name not in {'.env.example','.env.airgap.example'}:
        for m in ASSIGN.finditer(txt):
            value=m.group(2).strip()
            if len(value)>=20 and not any(a in value.lower() for a in ALLOW) and entropy(value)>=3.5:
                issues.append((p,txt.count('\n',0,m.start())+1,'high-entropy-sensitive-assignment'))
if issues:
    for p,l,k in issues: print(f'FAIL {p.relative_to(ROOT)}:{l} {k}')
    raise SystemExit(f'Secret scan failed: {len(issues)} finding(s)')
print('PASS: deterministic source secret scan found 0 committed secret candidates')
