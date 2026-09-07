from __future__ import annotations
import json, os, sys, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=Path(tempfile.gettempdir())/'mgc_languages_v571.db'
try: DB.unlink()
except FileNotFoundError: pass
EVID=Path(tempfile.mkdtemp(prefix='mgc-v571-evidence-'))
os.environ.update({
    'DATABASE_URL':f'sqlite:///{DB}','AUTO_CREATE_SCHEMA':'true','APP_ENV':'pilot','AUTH_MODE':'local','REGISTRATION_ENABLED':'true',
    'TRUSTED_HOSTS':'testserver,localhost,127.0.0.1','MGC_ADMIN_USERNAME':'v571admin','MGC_ADMIN_PASSWORD':'V571AdminPassword!123456',
    'MGC_ADMIN_DISPLAY_NAME':'v571 Admin','OIDC_STATE_SECRET':'v571-test-secret-32-bytes-long-000001','TTS_LEGACY_GET_ENABLED':'false',
    'TERM_APPROVAL_REQUIRED':'true','RLS_ENABLED':'true','METRICS_TOKEN':'v571metrics','RECOVERY_EVIDENCE_REQUIRED':'true',
    'BACKUP_EVIDENCE_DIR':str(EVID),'WAL_ARCHIVE_DIR':str(EVID/'wal'),'BACKUP_MAX_AGE_MINUTES':'1560','RESTORE_EVIDENCE_MAX_AGE_DAYS':'30',
    'RPO_TARGET_MINUTES':'1440','RTO_TARGET_MINUTES':'60','DB_SLOW_QUERY_THRESHOLD_MS':'500',
})
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient  # noqa
import app  # noqa

assert app.APP_VERSION=='5.7.1'
assert app.EXPECTED_ALEMBIC_HEAD=='c57d0a31f570'

# Evidence files are metadata-only and can be observed without making recovery status part of readiness.
(EVID/'mgc_languages_20260907T010000Z.dump').write_bytes(b'pilot-backup-placeholder')
(EVID/'restore_evidence_20260907.restore-ok.json').write_text(json.dumps({
    'verified_at':'2026-09-07T01:10:00Z','dump':'mgc_languages_20260907T010000Z.dump','duration_seconds':42,'result':'PASS'
}),encoding='utf-8')
(EVID/'wal').mkdir(exist_ok=True)
(EVID/'wal'/'000000010000000000000001').write_bytes(b'wal-placeholder')

admin=TestClient(app.app)
r=admin.post('/api/login',json={'username':'v571admin','password':'V571AdminPassword!123456'})
assert r.status_code==200,r.text

# Generate DB activity. Query telemetry must expose timing/fingerprints, never SQL text/parameters.
for _ in range(4):
    assert admin.get('/api/meta').status_code==200
    assert admin.get('/api/admin/system/summary').status_code==200
with app._DB_QUERY_LOCK:
    app._DB_QUERY_WINDOW.append((time.time(), 900.0, 'deadbeefcafefeed', 'SELECT', True))
    app._DB_QUERY_TOTAL['queries'] += 1
    app._DB_QUERY_TOTAL['slow_queries'] += 1
telemetry=admin.get('/api/admin/database/telemetry')
assert telemetry.status_code==200,telemetry.text
q=telemetry.json()['queries']
assert q['queries']>=1 and q['slow_queries']>=1 and q['p95_ms']>=0
assert q['top_slow_fingerprints'] and q['top_slow_fingerprints'][0]['fingerprint']
assert 'sql' not in q['top_slow_fingerprints'][0] and 'parameters' not in q['top_slow_fingerprints'][0]
assert 'SQL text and parameters are not stored' in q['privacy_note']

recovery=admin.get('/api/admin/recovery/evidence')
assert recovery.status_code==200,recovery.text
rv=recovery.json()
assert rv['backup']['status']=='ok',rv
assert rv['restore_rehearsal']['status']=='ok',rv
assert rv['objectives']['rpo_status']=='met',rv
assert rv['objectives']['rto_status']=='met' and rv['objectives']['last_restore_duration_minutes']<1,rv

summary=admin.get('/api/admin/system/summary')
assert summary.status_code==200
sj=summary.json(); assert 'database_observability' in sj and 'recovery_evidence' in sj and 'rpo_rto' in sj

dash=admin.get('/api/admin/it-dashboard')
assert dash.status_code==200,dash.text
d=dash.json(); assert 'query_telemetry' in d['database'] and 'pool' in d['database'] and 'recovery_evidence' in d and 'rpo_rto' in d

metrics=admin.get('/metrics',headers={'Authorization':'Bearer v571metrics'})
assert metrics.status_code==200,metrics.text
for name in ('mgc_db_query_p95_ms','mgc_db_slow_queries_window','mgc_db_pool_saturation_percent','mgc_recovery_backup_age_minutes','mgc_recovery_restore_evidence_age_days','mgc_recovery_rpo_target_minutes','mgc_recovery_rto_target_minutes'):
    assert name in metrics.text,name

# Non-admin cannot access operational details.
user=TestClient(app.app)
rr=user.post('/api/register',json={'username':'v571user','password':'StrongPass123!','display_name':'v571 User'})
assert rr.status_code==200,rr.text
assert user.get('/api/admin/database/telemetry').status_code==403
assert user.get('/api/admin/recovery/evidence').status_code==403

# Deployment/static contracts.
compose=(ROOT/'docker-compose.pilot.yml').read_text()
assert './backups:/backups:ro' in compose and 'wal_archive:/wal_archive:ro' in compose
assert 'RECOVERY_EVIDENCE_REQUIRED' in compose and 'DB_SLOW_QUERY_THRESHOLD_MS' in compose
restore=(ROOT/'scripts/restore_rehearsal.sh').read_text()
assert 'duration_seconds' in restore and '.restore-ok.json' in restore
frontend=(ROOT/'static/app.js').read_text()
assert 'Slow-query fingerprints' in frontend and 'backup age' in frontend and 'restore evidence' in frontend

print('OK: v5.7.1 privacy-safe DB telemetry, pool/recovery evidence, RPO/RTO and Admin/IT contracts')
