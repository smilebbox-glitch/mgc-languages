# MGC Engineering AI Local v6.3.14 — Data Consistency & Disaster Recovery

## Goal

Prevent a backup from being declared usable when PostgreSQL, evidence files or the Digital Thread represent different points in time, and prevent a restore from reopening engineering work merely because containers are healthy.

## Release boundary

- Application: **6.3.14**
- Database schema: **6.3.13**
- Database migration: **none**
- Automotive business behavior: unchanged
- Main scope: backup consistency epochs, exact restore verification, corruption detection and PITR readiness

## Authoritative consistency scanner

`backend/app/services/dr_consistency.py` performs a maintenance-grade scan of:

1. PostgreSQL logical row content in deterministic table/primary-key order;
2. PostgreSQL public sequence state when PostgreSQL is used;
3. database schema marker;
4. controlled document file existence, size and SHA-256;
5. evidence-storage tree SHA-256;
6. symlinks in authoritative evidence storage — fail-closed;
7. scalar and JSON-list document references across engineering tables;
8. document activity hash chains and their head/count anchors;
9. engineering change hash chains and their head/count anchors.

The scanner distinguishes critical findings from rebuildable warnings such as a missing derived preview.

## Backup v2

`BACKUP_MANIFEST.json` is now `mgc-core-backup-v2` and binds the backup to:

- `CONSISTENCY_SNAPSHOT.json`;
- consistency epoch ID;
- database logical SHA-256;
- storage tree SHA-256;
- application/schema version;
- quiesce status and stopped service set;
- artifact-level SHA-256 values.

A default v6.3.14 backup requires both full file hashing and full logical database hashing.

## Execution-plane quiesce

The backup workflow closes ingress and scheduler first, allows managed jobs to drain, then stops all resource worker classes. The API is kept private only long enough to compute the consistency report and optional Qdrant snapshot, then stopped before PostgreSQL/evidence capture.

This is deliberately stricter than killing a Celery worker mid-write. If managed work cannot reach a safe boundary within the configured drain timeout, the default backup fails.

## Restore verification

A v2 restore computes the authoritative fingerprint again **before** reopening API traffic or background execution. It compares:

- consistency snapshot schema;
- database schema version;
- PostgreSQL logical SHA-256;
- evidence-storage tree SHA-256;
- zero critical findings in the restored state.

Failure is fail-closed: gateway, worker classes and API remain stopped for investigation.

## PITR

Optional `docker-compose.pitr.yml` is activated by `MGC_PITR_ENABLED=true`. It requests PostgreSQL WAL archiving to `MGC_PITR_ARCHIVE_PATH`.

Target-host status can be checked from the running API container:

```bash
./scripts/stack.sh exec -T api python - <<'PY'
import json
from sqlalchemy import text
from app.db.session import SessionLocal
with SessionLocal() as db:
    c=db.connection()
    out={
      'wal_level': c.execute(text('SHOW wal_level')).scalar_one(),
      'archive_mode': c.execute(text('SHOW archive_mode')).scalar_one(),
      'archive_timeout': c.execute(text('SHOW archive_timeout')).scalar_one(),
      'checkpoint_lsn': c.execute(text('SELECT pg_current_wal_lsn()::text')).scalar_one(),
      'in_recovery': bool(c.execute(text('SELECT pg_is_in_recovery()')).scalar_one()),
    }
    command=str(c.execute(text('SHOW archive_command')).scalar_one() or '')
    out['archive_command_configured']=bool(command.strip()) and command.strip() not in {'(disabled)',''}
    print(json.dumps(out,indent=2))
PY
```

Do not print or export the actual `archive_command`; the operational status intentionally exposes only whether it is configured.

## Security / safety properties

- no `.env`, API key, OIDC secret or PKI material enters the backup manifest;
- symlinks in authoritative evidence storage fail the consistency scan;
- document paths escaping the configured storage root fail the scan;
- unquiesced backup is non-certifiable;
- legacy v1 restore requires explicit weaker-evidence acceptance;
- exact restore mismatch keeps ingress/execution closed;
- PITR archive path is deployment configuration, not an automatically trusted offsite backup.

## Production certification still required

A corporate target host must still prove:

- real `docker compose build`/approved images;
- approved CVE/SCA/image scans;
- production PostgreSQL backup + restore drill;
- WAL archive durability and retention on separate protected storage;
- point-in-time recovery to a chosen timestamp/LSN;
- representative dataset duration and RPO/RTO measurement;
- OIDC/PKI and engineer smoke tests after recovery.

v6.3.14 provides the controls and fail-closed verification path; it does not fabricate those target-host results.
