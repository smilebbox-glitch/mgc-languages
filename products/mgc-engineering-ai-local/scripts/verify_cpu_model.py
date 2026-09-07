#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path
root=Path(sys.argv[1] if len(sys.argv)>1 else 'models/cpu').resolve()
manifest=root/'CPU_MODEL_MANIFEST.json'
if not manifest.is_file(): raise SystemExit(f'missing {manifest}')
data=json.loads(manifest.read_text(encoding='utf-8')); p=root/data['filename']
if not p.is_file(): raise SystemExit(f'missing CPU model {p}')
h=hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda:f.read(8*1024*1024), b''): h.update(chunk)
if h.hexdigest()!=data['sha256']: raise SystemExit(f'CPU model checksum mismatch: {p.name}')
print(f'CPU MODEL MANIFEST: OK ({p.name}, {p.stat().st_size/1024**3:.2f} GiB)')
