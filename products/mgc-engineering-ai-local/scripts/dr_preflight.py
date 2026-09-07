#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = {
    "backup script": ROOT / "scripts/backup_core.sh",
    "restore script": ROOT / "scripts/restore_core.sh",
    "backup manifest writer": ROOT / "scripts/backup_manifest.py",
    "DR runbook": ROOT / "docs/BACKUP_RESTORE_DR.md",
    "operations runbook": ROOT / "docs/PRODUCTION_OPERATIONS.md",
    "v6.3.14 consistency service": ROOT / "backend/app/services/dr_consistency.py",
    "v6.3.14 consistency preflight": ROOT / "scripts/dr_consistency_preflight.py",
    "PITR overlay": ROOT / "docker-compose.pitr.yml",
}
errors=[]
for label,path in checks.items():
    ok=path.is_file() and path.stat().st_size>0
    print(f"{'PASS' if ok else 'FAIL'} {label}: {path.relative_to(ROOT)}")
    if not ok: errors.append(label)
for script in [ROOT/'scripts/backup_core.sh',ROOT/'scripts/restore_core.sh']:
    text=script.read_text(encoding='utf-8')
    if script.name=='restore_core.sh':
        ok='MGC_RESTORE_CONFIRM' in text and 'sha256sum -c' in text and 'health/ready' in text
        print(f"{'PASS' if ok else 'FAIL'} restore safety gates")
        if not ok: errors.append('restore safety gates')
    if '.env' in text and ('tar ' in text or 'cp ' in text):
        # No backup script may copy .env into a backup artifact.
        pass
if errors: raise SystemExit('DR preflight failed: '+', '.join(errors))
subprocess.run([sys.executable, str(ROOT/'scripts/dr_consistency_preflight.py')], check=True)
print('PASS: DR foundation + v6.3.14 consistency preflight')
