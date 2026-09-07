# Backup, Restore & Disaster Recovery — v6.3.14

## Recovery model

MGC distinguishes **authoritative engineering state** from rebuildable acceleration/projection state.

### Authoritative — must restore as one consistency epoch

1. **PostgreSQL** — engineering/business records, ACL/governance state, BOM, changes, work instructions, release evidence, audit chains, background-job ledger and projection outbox.
2. **Evidence storage** (`storage/`) — uploaded controlled source files and other local evidence referenced by PostgreSQL.

### Derived / rebuildable

- Qdrant vector index — optional snapshot may reduce recovery time, but PostgreSQL + evidence remain authoritative.
- Neo4j graph projection — rebuildable.
- `engineering_read_models` and Redis cache/queue state — rebuildable/transient.
- model weights and container images — deployment artifacts, not engineering records.
- `.env`, OIDC/API secrets and PKI material — corporate secret-management responsibility and intentionally excluded.

## v6.3.14 consistency epoch

A backup is not considered certifiable merely because `pg_dump` and `storage.tar.gz` exist. The backup workflow now creates `CONSISTENCY_SNAPSHOT.json` while the write-capable execution plane is quiesced.

The snapshot contains:

- release and database schema version;
- unique consistency epoch ID;
- deterministic logical SHA-256 over ORM-managed PostgreSQL table rows and PostgreSQL sequence state;
- current PostgreSQL WAL checkpoint/archiving posture when available;
- deterministic SHA-256 of the authoritative evidence-storage tree;
- per-document size/SHA-256 validation against PostgreSQL metadata;
- dangling document-reference detection across the Digital Thread;
- tamper-evident document activity-chain verification;
- tamper-evident engineering-change event-chain verification.

Any critical finding makes the snapshot `FAIL` and the default backup workflow stops fail-closed.

## Quiesce / clean-drain policy

Default backup order:

1. close user ingress (`gateway`) and scheduler (`beat`);
2. allow managed `ComputeJob` work to reach a safe boundary for up to `MGC_BACKUP_DRAIN_TIMEOUT_SECONDS`;
3. refuse the authoritative backup if jobs are still `running` and `MGC_BACKUP_REQUIRE_CLEAN_DRAIN=true`;
4. stop **all** resource workers: `worker`, `worker-cpu`, `worker-io`, `worker-cad`, `worker-ai`;
5. generate the full consistency snapshot;
6. optionally capture a Qdrant snapshot;
7. stop the private API;
8. create PostgreSQL dump and evidence archive while no normal application writer is running;
9. create `BACKUP_MANIFEST.json` schema `mgc-core-backup-v2` and verify all SHA-256 files;
10. restore services that the backup workflow itself stopped.

This closes the earlier gap where only the base worker was quiesced while CPU/IO/CAD/AI workers could still write.

Separately deployed ingress (for example an independently managed webhook edge or an external integration process) must be included in the same approved maintenance window. MGC cannot prove quiescence of infrastructure it does not control.

## Backup command

```bash
make backup
```

or:

```bash
./scripts/backup_core.sh /approved/backup/location/mgc-YYYYMMDD
```

Typical v2 set:

```text
postgres.dump
storage.tar.gz
CONSISTENCY_SNAPSHOT.json
qdrant.snapshot                 # optional/rebuildable
BACKUP_MANIFEST.json
SHA256SUMS
```

`MGC_BACKUP_QUIESCE=false` is rejected by default. `MGC_ALLOW_UNQUIESCED_BACKUP=true` may create an emergency copy, but its manifest is marked `certifiable_authoritative_backup=false` and restore requires an explicit override.

## Restore command

Restore is destructive and requires an explicit guard:

```bash
MGC_RESTORE_CONFIRM=RESTORE ./scripts/restore_core.sh /approved/backup/location/mgc-YYYYMMDD
```

By default the workflow first creates a safety backup of the current state. Skipping it requires `MGC_SKIP_PRE_RESTORE_BACKUP=true` and should be linked to an approved incident/change record.

### v2 restore order

1. verify backup artifact SHA-256 values;
2. verify the v2 manifest policy;
3. create a pre-restore safety backup unless explicitly waived;
4. stop gateway, beat, all workers and API;
5. restore PostgreSQL into a clean `public` schema;
6. replace authoritative evidence storage;
7. start a one-shot private application container and compute a new full authoritative fingerprint;
8. compare database logical SHA-256 and evidence-tree SHA-256 with the recorded backup epoch;
9. **if any comparison fails, leave API/gateway/workers stopped**;
10. restore optional Qdrant snapshot;
11. start only the private API and require liveness/readiness;
12. reopen workers, scheduler and gateway;
13. observe/rebuild derived projections and execute engineer smoke tests.

A green `/ready` response is necessary but is no longer sufficient to declare recovery successful. Exact authoritative-state comparison happens first.

### Legacy backup handling

`mgc-core-backup-v1` did not contain a full consistency fingerprint. v6.3.14 therefore refuses a v1 restore unless an operator explicitly supplies:

```bash
MGC_ALLOW_LEGACY_RESTORE=true
```

This is an acceptance of weaker evidence, not an upgrade of the legacy backup.

## PostgreSQL PITR readiness

v6.3.14 adds an **optional** Compose overlay `docker-compose.pitr.yml`. When:

```text
MGC_PITR_ENABLED=true
MGC_PITR_ARCHIVE_PATH=/approved/separately-protected/wal/archive
```

`stack.sh` adds the overlay and requests PostgreSQL WAL archiving with:

- `wal_level=replica`;
- `archive_mode=on`;
- bounded `archive_timeout`;
- `archive_command` copying completed WAL files to the configured archive path.

The archive target must be a separately protected corporate backup target and writable by the PostgreSQL container identity. A directory on the same unprotected disk as `pg_data` does **not** satisfy production DR.

The consistency snapshot records the current WAL LSN and sanitized PITR posture. On a running target, validate actual settings with the in-container PITR status check described in `DATA_CONSISTENCY_DR_v6.3.14.md`.

MGC does not claim PITR certification until a target-host drill proves base backup + WAL replay to a selected recovery timestamp/LSN.

## RPO / RTO

The software does not invent corporate RPO/RTO values. Business, R&D, IT and Security must agree them from measured recovery exercises.

For pilot certification evidence, record at minimum:

- backup consistency epoch ID;
- backup manifest and SHA-256 verification;
- source application/schema version;
- clean-drain result and quiesced services;
- database logical fingerprint before/after restore;
- evidence-tree fingerprint before/after restore;
- critical/warning integrity findings;
- PostgreSQL WAL LSN/PITR posture;
- Qdrant restore or controlled projection rebuild status;
- readiness response;
- engineer authentication and unauthorized-user rejection;
- sample source-document retrieval and SHA-256 verification;
- sample BOM, WI, change and release-baseline retrieval;
- measured backup/recovery duration;
- incident/change ticket reference.

## Known boundaries

- Application-level backup does not replace storage-array snapshots, PostgreSQL physical replication, immutable/offsite backups, backup-encryption policy or enterprise backup appliances.
- `docker-compose.pitr.yml` is a deployment mechanism, not proof that WAL is copied off-host or retained correctly.
- Qdrant/Neo4j/read models remain derived and may need controlled convergence after restore.
- Full logical/database and evidence hashing is intentionally I/O intensive; run it in a maintenance window and certify duration using representative automotive datasets.
