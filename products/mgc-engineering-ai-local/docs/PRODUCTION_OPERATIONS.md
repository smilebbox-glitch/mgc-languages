# MGC Engineering AI Local v6.0.9 — Production Operations Runbook

## Purpose

This runbook covers day-2 operation of the on-prem / air-gapped Engineering Intelligence platform. It does not replace corporate infrastructure, database, backup, SOC or disaster-recovery standards.

## Service health contract

| Endpoint | Meaning | Downstream I/O | Intended use |
|---|---|---:|---|
| `/api/v1/health` | backward-compatible liveness | No | legacy probes |
| `/api/v1/health/live` | process is alive | No | container/process liveness |
| `/api/v1/health/ready` | required operational dependencies are usable | Yes | load-balancer/readiness gate |
| `/metrics` | Prometheus metrics on private API network | N/A | Prometheus only; not gateway-routed |

Readiness always requires:

- PostgreSQL connectivity;
- expected MGC schema marker (`6.0.9`);
- evidence storage read/write access.

By default it also requires Redis and Qdrant. Neo4j and MinIO are required only when their feature flags are enabled. Local LLM/VLM is **not** a readiness gate because deterministic engineering workflows must remain available during inference degradation.

Health responses intentionally omit connection URLs, host paths, credentials and raw exception messages.

## Startup / schema migration safety

Application startup performs only additive/idempotent schema work. v6.0.1 serializes startup schema changes with a PostgreSQL advisory lock and fails after a bounded timeout rather than allowing multiple replicas to race indefinitely.

Operational rule:

1. deploy one API replica first during schema transition;
2. wait for `/health/ready` = `ready`;
3. only then scale additional API/worker replicas;
4. never bypass a failed schema readiness check.

`MIGRATION_LOCK_TIMEOUT_SECONDS` defaults to 60 seconds.

## Operational logs

The API emits privacy-minimized structured request events containing only:

- request ID;
- HTTP method;
- resolved **route template**;
- response status;
- duration.

It does **not** log request/response bodies, query strings, user identity, authorization headers, VINs or part numbers embedded in concrete paths. `X-Request-ID` is returned to the caller for incident correlation.

## Prometheus signals

In addition to FastAPI request metrics, v6.0.1 exposes:

- `mgc_operational_readiness`;
- `mgc_dependency_up{dependency=...}`;
- `mgc_dependency_check_latency_ms{dependency=...}`.

Recommended alerts:

- readiness = 0 for 2 minutes → critical;
- database or evidence storage dependency = 0 → critical;
- Redis/Qdrant required dependency = 0 → high;
- sustained p95 API latency breach → high;
- repeated container restarts → high;
- disk free capacity below corporate threshold → high.

## Minimum daily checks

```bash
./scripts/stack.sh ps
./scripts/stack.sh exec -T api python - <<'PY'
import json, urllib.request
print(json.dumps(json.loads(urllib.request.urlopen(
    'http://127.0.0.1:8080/api/v1/health/ready', timeout=10
).read()), ensure_ascii=False, indent=2))
PY
```

Then review:

- failed/background jobs;
- storage capacity;
- database capacity/replication according to DBA standard;
- backup completion and checksum validation;
- security alerts and failed SSO attempts at the corporate edge.

## Incident severity suggestion

### SEV-1

- evidence integrity risk;
- unauthorized data exposure;
- database corruption;
- release/configuration records unavailable during a critical engineering gate.

Action: remove user traffic, preserve logs/evidence, engage IT/Security/Engineering owner.

### SEV-2

- core API not ready;
- Qdrant/Redis outage blocking normal work;
- sustained major performance degradation.

### SEV-3

- optional local inference unavailable while deterministic core remains usable;
- Neo4j optional projection degraded;
- non-critical integration delayed.

## Maintenance-window sequence

1. create and verify a backup;
2. stop external write entry/background worker;
3. apply release/build changes;
4. start private API;
5. verify `/health/live` then `/health/ready`;
6. run migration/security/acceptance gates;
7. restore worker and user traffic;
8. perform one allowed-engineer smoke test and one denied-user authorization test.

## Capacity and SRE work still required before enterprise-wide rollout

v6.0.1 establishes operational primitives but does not claim enterprise-scale certification. The production hardening program still requires measured benchmarks for large BOM/VIN/quality datasets, centralized log retention, infrastructure-level PostgreSQL HA, disk/volume monitoring, penetration testing and a tested site-level DR procedure.


## v6.0.2 integration operations

For each external source, monitor both transport health and evidence quality. `health=ok` does not imply current/complete engineering data. Use `/api/v1/integrations/{system_id}/quality` and Prometheus `mgc_integration_data_confidence` / `mgc_integration_quarantine_events`. A growing quarantine count is an operational incident for the integration owner; replay requires Engineering Admin and never bypasses the current contract. PostgreSQL sync advisory locks serialize one source sync across replicas.


## v6.0.4 reconciliation operations

Treat mapping drift and source disagreement as operational integration incidents, not as data to be silently normalized. Review the v6.0.4 reconciliation cockpit for the pilot project after every material source-system mapping/configuration change. A stale alias must be reverified against the current source fingerprint before it is eligible for reconciliation. Source-of-truth conflicts require an explicit corporate owner decision; MGC does not select or write a winner back to source systems.

## v6.0.5 enterprise security operations

For enterprise deployments use the dedicated security overlay, corporate PKI material outside the repository, corporate OIDC, separate runtime/migration PostgreSQL identities and mandatory build-host supply-chain gates. Run `make supply-chain-preflight`; before approval also rerun it with `MGC_REQUIRE_CVE_SCANNER=true MGC_REQUIRE_LOCKFILES=true`. Review `GET /api/v1/security/posture` and export audit evidence before material release/pilot decisions.

## v6.0.8 operational SLO / incident support

- `/api/v1/operations/summary` — admin operational summary;
- `/api/v1/operations/slo` — dependency SLO/error budget;
- `/api/v1/operations/health-samples` — explicit health snapshot;
- `/api/v1/operations/incidents` — operator incident evidence;
- `/api/v1/operations/support-bundle` — privacy-safe support bundle.

For continuous local health history enable `OPERATIONAL_SAMPLING_ENABLED=true`. The Celery Beat scheduler is hardened and uses runtime-only DB privileges in the enterprise overlay.


## v6.0.9 operations acceptance / game days

Use `make game-day-preflight` to validate the acceptance framework. Actual fault injection must be executed only on an approved non-production or controlled-pilot environment using `docs/GAME_DAY_RUNBOOK.md`. MGC records evidence and calculates RTO/MTTR/RPO; it never performs destructive fault injection and never authorizes production deployment.


## v6.3.2 Projection reliability

Projection health is operationally visible but non-gating for Core. Engineering Admins should inspect `GET /api/v1/operations/projections`, keep `dead_letter=0`, and investigate oldest-event lag above the configured threshold. Use controlled DLQ replay for corrected transient failures and `POST /api/v1/operations/projections/rebuild` after restoring/recreating a derived store. Do not clear PostgreSQL outbox/receipt rows as a shortcut.

## v6.3.14 consistency-verified disaster recovery

Production backup/restore must use `scripts/backup_core.sh` and `scripts/restore_core.sh` with the v6.3.14 consistency epoch controls. A certifiable backup quiesces gateway, scheduler and every resource worker class, drains managed jobs to a safe boundary, writes `CONSISTENCY_SNAPSHOT.json`, and binds its database/evidence fingerprints into `BACKUP_MANIFEST.json` v2.

Restore is fail-closed. PostgreSQL and authoritative evidence storage are restored first, then a new full consistency snapshot is computed and compared with the backup epoch **before** private API, workers or ingress are reopened. Health/readiness alone is not sufficient proof of recovery. A fingerprint mismatch keeps the stack in maintenance state.

Optional PostgreSQL WAL archiving is enabled only with `MGC_PITR_ENABLED=true` and `docker-compose.pitr.yml`; the target host must provide a protected `MGC_PITR_ARCHIVE_PATH`. Production certification still requires a real restore and point-in-time recovery drill with measured RPO/RTO.
