from __future__ import annotations
import hashlib, sys
from pathlib import Path
if len(sys.argv)<2: raise SystemExit('Usage: verify_backup_artifacts.py <backup-file> [...]')
for raw in sys.argv[1:]:
    p=Path(raw); side=Path(str(p)+'.sha256')
    if not p.is_file(): raise SystemExit(f'MISSING: {p}')
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    if side.is_file():
        expected=side.read_text().strip().split()[0]
        if h != expected: raise SystemExit(f'HASH MISMATCH: {p}')
    print(f'PASS {p.name} sha256={h}')
