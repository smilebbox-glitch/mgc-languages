# MGC Languages v5.7.1 — Observability & Recovery hardening

Patch release on top of v5.7. No database migration is required; Alembic head remains `c57d0a31f570`.

## Database observability
- SQLAlchemy query-timing instrumentation with a bounded in-process window.
- Slow-query threshold and alerting are environment-driven.
- Query fingerprints are SHA-256 hashes of normalized statements; raw SQL and parameters are not retained.
- PostgreSQL pool capacity, checked-out connections and saturation are exposed to Admin/Prometheus.
- New Admin endpoint: `GET /api/admin/database/telemetry`.

## Recovery evidence / RPO-RTO
- Admin recovery view reads the newest backup artifact and restore-rehearsal evidence.
- `restore_rehearsal.sh` records measured restore duration in `*.restore-ok.json`.
- RPO target is compared with observed backup age; RTO status uses measured restore duration when available.
- Recovery evidence is operational alerting only and intentionally does not make readiness fail.
- New Admin endpoint: `GET /api/admin/recovery/evidence`.
- `recovery_evidence_check.py` validates backup/restore evidence from the command line.
- `postgres_failure_drill.sh` provides a guarded sandbox-only DB outage/recovery drill.

## Pilot backup worker
- `docker-compose.pilot.yml` includes an internal PostgreSQL backup service.
- Default interval: 24h; default retention: 14 days.
- Dumps and checksums are written to `./backups`.
- App mounts backup evidence and pilot WAL archive read-only.
- Same-host backup/WAL is rehearsal-grade only; production requires encrypted off-host durability.

## Observability UI / alerts
- IT Dashboard now shows DB query p95, slow-query count, pool saturation, backup age and restore evidence age.
- Prometheus metrics and alert rules cover DB pool saturation, slow queries, stale/missing backup evidence and stale/missing restore rehearsal evidence.
- Grafana dashboard extended with DB and recovery panels.

## Release engineering
- Added `v571` regression shard.
- Runtime acceptance checks v5.7.1 observability/recovery endpoints and metrics.
