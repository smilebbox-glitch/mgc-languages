# MGC Engineering AI Local v6.3.30 — Production Observability & Automated Incident Evidence

## Scope

v6.3.30 extends the existing v6.0.8 operations layer. It does **not** introduce a second monitoring stack, a new engineering domain, or autonomous remediation.

The new layer converts existing privacy-safe runtime observations into deterministic incident evidence for Engineering Admin and IT operations.

Application version: **6.3.30**  
Database schema: **6.3.13**  
Database migration: **none**

## Signal sources

The evaluator consumes existing bounded operational snapshots only:

- readiness / required dependency failures;
- dependency SLO and error-budget state;
- managed queue age;
- PLM/PDM/ERP/MES/QMS freshness compliance;
- projection/read-model health;
- compute-job DLQ, orphaned jobs and expired leases;
- optional-dependency brownout;
- runtime version skew;
- application HA, authoritative data/evidence HA and multi-host topology safety.

No raw log line, SQL statement, engineering document, query, VIN/part history, credential or source payload is copied into the incident evidence report.

## Evidence contract

Schema: `mgc.production-incident-evidence.v1`.

Each signal has a bounded code, severity, component, deterministic SHA-256 signal fingerprint and a sanitized evidence subset. The complete report is canonical-JSON hashed with SHA-256.

Governance invariants are explicit in every report:

- `contains_raw_logs=false`;
- `contains_document_content=false`;
- `contains_queries=false`;
- `contains_credentials=false`;
- `automatic_destructive_recovery=false`;
- `automatic_incident_resolution=false`;
- `production_authorized=false`;
- `human_operator_required=true`.

## Incident materialization

Evidence generation is always available and read-only.

Optional automatic materialization into the existing `ProductionIncident` table is controlled by:

```text
AUTOMATED_INCIDENT_MATERIALIZATION_ENABLED=false
```

Default is **false** for backward compatibility.

When enabled, periodic operational sampling may create one open incident per active signal fingerprint and refresh the same open incident on later samples. Severity can only be escalated automatically. A clear sample never closes an incident.

Resolved incidents are never reopened automatically. If the same signal remains or recurs after human resolution, a later sampling pass may create a new incident episode.

## API

Engineering Admin only:

```text
GET  /api/v1/operations/incident-evidence
POST /api/v1/operations/incident-evidence/reconcile
```

`GET` is side-effect free. `POST` reconciles the current evidence and records an audit event; DB materialization occurs only when `AUTOMATED_INCIDENT_MATERIALIZATION_ENABLED=true`.

## Support bundle

The existing privacy-safe support bundle now includes:

```text
incident-evidence.json
```

The bundle continues to exclude raw logs and proprietary engineering payloads.

## Metrics

Prometheus exposes only bounded severity cardinality:

```text
mgc_incident_evidence_signals{severity="low|medium|high|critical"}
```

User names, VINs, part numbers, document IDs, query strings and signal fingerprints are intentionally not metric labels.

## Safety boundary

v6.3.30 can detect, record and correlate runtime symptoms. It cannot:

- restart services;
- promote PostgreSQL;
- change LB routing;
- replay destructive integration writes;
- close incidents automatically;
- modify engineering source-of-truth data;
- authorize production.

Existing target-host assurance, load/SLO certification, supply-chain/CVE evidence, integration certification and human change approval remain independent gates.
