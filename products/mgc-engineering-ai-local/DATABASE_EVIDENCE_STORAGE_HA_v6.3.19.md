# MGC Engineering AI Local v6.3.19 — Database & Evidence Storage HA

## Goal

v6.3.19 closes the next application-level safety gap after v6.3.18 HA: MGC must not accept authoritative engineering writes merely because an API container is alive. When authoritative HA is enabled, writes are permitted only while the connected PostgreSQL target is a writable primary and the mounted evidence storage generation is explicitly active and bound to the approved data cluster.

No automotive-domain table changes are introduced. Application version is **6.3.19** and database schema remains **6.3.13**.

## Responsibility boundary

MGC does **not** implement a PostgreSQL consensus system, synchronous block/file replication, STONITH, quorum or zone-level load balancing. Production HA still requires approved external infrastructure such as Patroni/repmgr/cloud-managed PostgreSQL plus fencing, and shared/replicated evidence storage with its own durability/replication controls.

MGC adds the application-side fail-closed controls that those systems cannot infer from engineering semantics:

- PostgreSQL role verification with `pg_is_in_recovery()`;
- `transaction_read_only` verification;
- optional exact PostgreSQL `system_identifier` pinning using `pg_control_system()`;
- evidence cluster/generation marker verification;
- binding of evidence generation to the PostgreSQL cluster identity;
- global HTTP mutation fencing;
- `Session.before_flush` + bulk ORM UPDATE/DELETE + final `before_commit` fencing for Celery/maintenance/non-HTTP writes;
- readiness, Prometheus, Operations and support-bundle diagnostics;
- consistency-bound HA recovery points and guarded evidence promotion.

## Authoritative write fence

When `DATABASE_HA_ENABLED=true` or `EVIDENCE_HA_ENABLED=true`, the authoritative write gate evaluates both sides of the engineering transaction boundary.

A write is allowed only when:

1. PostgreSQL is reachable through the configured writer VIP/DNS;
2. the server reports `pg_is_in_recovery() = false`;
3. `transaction_read_only = off`;
4. the optional configured PostgreSQL `system_identifier` matches exactly;
5. `mgc_schema_state` exists and equals runtime schema `6.3.13`;
6. the evidence marker exists and uses schema `mgc-evidence-ha-marker-v1`;
7. its `cluster_id` matches `EVIDENCE_HA_CLUSTER_ID`;
8. its generation is valid and `state=active`;
9. if the marker is database-bound, its PostgreSQL system identifier matches the connected database cluster.

Failure returns HTTP 503 `AUTHORITATIVE_WRITE_FENCED` for mutating API calls and rejects transaction commit for background/maintenance sessions. GET/HEAD traffic can still be used for diagnostics when the surrounding deployment policy permits it.

## Evidence generation marker

Default marker path:

```text
/data/storage/.mgc-ha/STORAGE_EPOCH.json
```

`.mgc-ha` is **operational fencing metadata**, not engineering evidence. It is therefore excluded from:

- DR evidence-tree fingerprints;
- authoritative evidence backup archives.

For replicated-failover storage, `.mgc-ha` must also be target-local and excluded from the external replication payload. Copying an `active` marker to a standby defeats the fence and is prohibited. Marker path components are rejected when they are symlinks, even if the symlink target stays inside the storage root. Marker updates use atomic replace plus file/directory `fsync` so a crash cannot silently turn a partial marker write into authority.

Initialize a target:

```bash
python scripts/evidence_ha_marker.py \
  --storage /data/storage init \
  --cluster-id mgc-evidence-prod-01 \
  --database-system-identifier <approved-id> \
  --state standby
```

Demote:

```bash
python scripts/evidence_ha_marker.py --storage /data/storage demote --confirm DEMOTE_EVIDENCE
```

## Consistency-bound recovery point

Before a controlled failover, create a full logical database + evidence SHA-256 recovery point:

```bash
PYTHONPATH=backend python scripts/authoritative_recovery_point.py \
  --output /secure-ha-evidence/recovery-point.json
```

The command refuses to produce a point unless:

- the connected PostgreSQL primary is proven writable and approved;
- the evidence generation is active;
- full database logical hashing passes;
- full evidence hashing passes;
- document references and tamper-evident chains pass.

The file records the PostgreSQL cluster identifier, WAL LSN when available, logical DB hash, evidence tree hash, evidence cluster/generation and consistency epoch. It always records `production_authorized=false`.

## Evidence promotion

After the **external** PostgreSQL/storage failover mechanism has completed and the target data set is known to correspond to the approved recovery point, evidence promotion is explicit:

```bash
python scripts/evidence_ha_marker.py \
  --storage /data/storage promote \
  --cluster-id mgc-evidence-prod-01 \
  --database-system-identifier <approved-id> \
  --expected-generation 7 \
  --recovery-point /secure-ha-evidence/recovery-point.json \
  --confirm PROMOTE_EVIDENCE
```

Promotion increments the generation atomically. A stale expected generation, wrong cluster, wrong database identity or incomplete recovery point fails closed.

## Compose / deployment

The normal developer Compose topology remains unchanged. For an approved external PostgreSQL writer endpoint and shared/replicated evidence mount, use:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.ha.yml \
  -f docker-compose.authoritative-ha.yml \
  up -d
```

Required operator inputs include:

- `DATABASE_URL` — writer VIP/DNS, not an arbitrary replica;
- `DATABASE_HA_EXPECTED_SYSTEM_IDENTIFIER`;
- `MGC_STORAGE_PATH` — active shared/replicated evidence mount;
- `EVIDENCE_HA_CLUSTER_ID`.

The base Compose now permits `DATABASE_URL` and `MGC_STORAGE_PATH` overrides while preserving previous local defaults.

## Operations

Engineering Admin can inspect:

```text
GET /api/v1/operations/authoritative-ha
```

The same sanitized state is included in readiness, Prometheus and `authoritative-ha.json` inside the privacy-safe support bundle.

## Non-goals / mandatory external gates

v6.3.19 does **not** claim:

- automatic PostgreSQL promotion;
- database quorum or STONITH implementation;
- synchronous evidence replication;
- storage-controller fencing;
- multi-host/zone failover certification;
- zero-RPO guarantees;
- production authorization.

A real target-host drill must demonstrate primary loss, old-primary fencing, DB promotion, evidence generation promotion, application reconnect, write-fence reopening, consistency verification and rollback/forward-fix handling.
