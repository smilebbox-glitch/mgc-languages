# v5.7.1 Observability & Recovery

## Design boundary
This patch improves evidence and diagnosis. It does **not** turn same-host Docker Compose into a production disaster-recovery platform.

## Database telemetry
The app measures SQLAlchemy execution duration and keeps a bounded process-local timing window. It stores only:
- timestamp;
- duration;
- operation class (`SELECT`, `UPDATE`, etc.);
- a short SHA-256 fingerprint of normalized SQL;
- whether the configured slow-query threshold was exceeded.

SQL text, bind parameters, learning phrases and selected answers are not retained by this telemetry.

Useful environment variables:
- `DB_QUERY_WINDOW_MINUTES=15`
- `DB_SLOW_QUERY_THRESHOLD_MS=500`
- `DB_SLOW_QUERY_ALERT_COUNT=5`
- `DB_POOL_ALERT_PERCENT=80`

For a replicated deployment, Prometheus/OpenTelemetry should be the authoritative aggregated view; process-local windows reset on restart.

## Recovery evidence
The app reads evidence from `BACKUP_EVIDENCE_DIR` (pilot: `/backups`).
- newest `mgc_languages_*.dump` or base backup → observed backup age;
- newest `*.restore-ok.json` → restore-rehearsal age and measured duration;
- newest WAL archive file → informational pilot WAL signal.

Default pilot targets:
- `RPO_TARGET_MINUTES=1440`
- `RTO_TARGET_MINUTES=60`
- `BACKUP_MAX_AGE_MINUTES=1560`
- `RESTORE_EVIDENCE_MAX_AGE_DAYS=30`

RPO status is an estimate based on the latest visible backup artifact. RTO is only marked from a measured restore rehearsal duration; application uptime is not used as fake RTO evidence.

## Readiness boundary
Backup/restore evidence never makes `/health/ready` fail. A stale backup must alert IT, but it must not create an application outage. PostgreSQL/schema/security readiness failures still return 503.

## Pilot backup worker
The Compose `backup` service performs scheduled `pg_dump -Fc`, writes SHA-256, and applies retention. The app mounts `/backups` read-only.

This protects a pilot from simple data-loss scenarios but is not sufficient for production disaster recovery because the dump can still share the same host/failure domain. Production acceptance must verify off-host encrypted base backups/WAL, retention, access control, and restore drills.

## Controlled DB drill
`scripts/postgres_failure_drill.sh` pauses the pilot DB, proves live=200/ready=503, resumes PostgreSQL and waits for readiness recovery. It refuses to run unless `CONFIRM_PILOT_DRILL=YES` is explicitly supplied.
