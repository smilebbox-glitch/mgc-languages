# PostgreSQL Backup / PITR Preparation v5.7

Pilot Compose enables `wal_level=replica`, `archive_mode=on` and archives WAL into a dedicated Docker volume. This is useful for rehearsal, not sufficient production durability because the volume remains on the same Docker host.

Controls:
- daily logical `pg_dump` + SHA-256 (`backup_postgres.sh`);
- isolated restore rehearsal (`restore_rehearsal.sh`);
- PITR configuration check (`pitr_preflight.sh`);
- physical base backup helper (`pitr_basebackup.sh`);
- hash verifier (`verify_backup_artifacts.py`).

Production target: base backups and WAL must be copied to an approved off-host encrypted/object-storage target with lifecycle policy. DBA should document RPO/RTO and execute a timestamp-targeted restore rehearsal before production approval.
