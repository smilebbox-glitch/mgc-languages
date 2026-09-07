from __future__ import annotations
import argparse, json, os, time
from pathlib import Path

p=argparse.ArgumentParser(description='Validate MGC Languages backup/restore evidence without touching production data')
p.add_argument('--dir',default=os.getenv('BACKUP_EVIDENCE_DIR','./backups'))
p.add_argument('--backup-max-minutes',type=int,default=int(os.getenv('BACKUP_MAX_AGE_MINUTES','1560')))
p.add_argument('--restore-max-days',type=int,default=int(os.getenv('RESTORE_EVIDENCE_MAX_AGE_DAYS','30')))
a=p.parse_args(); root=Path(a.dir)

def latest(patterns):
    rows=[]
    if root.exists():
        for pattern in patterns: rows += [x for x in root.glob(pattern) if x.is_file()]
    return max(rows,key=lambda x:x.stat().st_mtime) if rows else None

def age_minutes(path): return (time.time()-path.stat().st_mtime)/60 if path else None
backup=latest(('mgc_languages_*.dump','mgc_languages_base_*.tar.gz'))
restore=latest(('*.restore-ok.json','restore_evidence_*.json'))
bage=age_minutes(backup); rage=age_minutes(restore)
report={'directory':str(root),'backup':{'file':backup.name if backup else None,'age_minutes':round(bage,2) if bage is not None else None},'restore':{'file':restore.name if restore else None,'age_days':round(rage/1440,2) if rage is not None else None}}
if restore:
    try: report['restore']['evidence']=json.loads(restore.read_text(encoding='utf-8'))
    except Exception: report['restore']['evidence_parse']='failed'
print(json.dumps(report,ensure_ascii=False,indent=2))
fail=[]
if bage is None or bage>a.backup_max_minutes: fail.append('backup evidence missing/stale')
if rage is None or rage/1440>a.restore_max_days: fail.append('restore rehearsal evidence missing/stale')
if fail:
    print('FAIL:', '; '.join(fail)); raise SystemExit(1)
print('PASS: recovery evidence is within configured pilot thresholds')
