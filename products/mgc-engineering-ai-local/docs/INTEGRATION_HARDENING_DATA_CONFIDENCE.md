# Integration Hardening & Data Confidence — v6.0.2

v6.0.2 strengthens the existing PLM/PDM/ERP/MES/QMS integration fabric without making MGC the source of truth for those systems.

## Integration contract

Each configured source declares:

- `source_domain`: `plm | pdm | erp | mes | qms | cad | files | engineering`;
- `contract_version`: currently `mgc-integration-v1`;
- `required_fields`: fields that must exist before the record may enter the controlled Digital Thread;
- `expected_freshness_minutes`: optional source-SLA used for freshness classification;
- optional `allowed_kinds` and future-clock-skew rules inside `config.integration_contract`.

The source record is validated before MGC treats it as controlled evidence. Validation failure goes to quarantine; stale-but-valid evidence remains visible with lower data confidence rather than disappearing.

## Data confidence

Confidence is intentionally explainable and is not a machine-learning score. The current aggregate is:

- schema validity: 35%;
- required-field completeness: 25%;
- freshness: 20%;
- stable identity: 10%;
- provenance: 10%.

The API always returns the component scores, freshness state, source domain and contract version together with the final `HIGH / MEDIUM / LOW` band.

`LOW` is not an automatic engineering rejection. It is a signal that evidence quality must be reviewed. Contract-invalid evidence is quarantined separately.

## Idempotency

A source-provided checksum / source timestamp / revision is preferred as the immutable source fingerprint. When the source supplies none of them, MGC downloads the payload and uses its SHA-256 digest for idempotency. This avoids silently skipping changed content when external metadata remains unchanged.

Every accepted/quarantined event receives an `integration_ingest_events` ledger entry with:

- source system and external ID;
- idempotency key;
- source revision / source timestamp;
- payload SHA-256 when available;
- contract validation result;
- data-quality breakdown;
- immutable document linkage;
- attempt count and timestamps.

## Quarantine / DLQ behavior

Contract-invalid content is copied to immutable local quarantine storage and is not indexed as a controlled engineering document. The synchronization checkpoint may still advance because the rejected event is durably recorded in the DLQ ledger.

Automatic polling does not endlessly retry the same quarantined event. Engineering Admin must either:

1. fix the adapter mapping / declared contract and explicitly replay the immutable payload; or
2. correct the authoritative source and run a normal source resynchronization.

Replay never bypasses validation. The payload is revalidated against the *current* contract before it can become controlled evidence.

## Structured MES/QMS records

`engineering_rest`, `erp_rest`, `mes_rest` and `qms_rest` can operate in `record_mode`. In this mode the source JSON record itself is serialized to immutable JSON evidence and no content-download endpoint is required.

Example:

```json
{
  "base_url": "http://qms-gateway.internal",
  "list_path": "/api/quality-events",
  "record_mode": true,
  "field_map": {
    "external_id": "event_id",
    "kind": "record_type",
    "modified_at": "updated_at"
  },
  "integration_contract": {
    "required_fields": ["external_id", "kind", "modified_at", "metadata.failure_code"],
    "expected_freshness_minutes": 30
  }
}
```

## Security boundaries

- credentials remain environment-variable references; raw secrets are not persisted through the API;
- quarantine filesystem paths are not returned to clients;
- source metadata cannot overwrite MGC-controlled provenance fields;
- imported document ACL is inherited from the configured integration ACL and is not widened by the source payload;
- integration admin endpoints require Engineering Admin;
- MGC never writes authoritative revisions, ERP transactions, MES production results or QMS dispositions back automatically.

## Operations

Prometheus exports:

- `mgc_integration_data_confidence{system=...}`;
- `mgc_integration_quarantine_events{system=...}`.

Primary API:

```text
GET  /api/v1/integrations
POST /api/v1/integrations/{system_id}/sync
GET  /api/v1/integrations/{system_id}/quality
GET  /api/v1/integrations/{system_id}/quarantine
POST /api/v1/integrations/{system_id}/quarantine/{event_id}/replay
```

See `docs/INTEGRATION_HARDENING_PILOT_ACCEPTANCE.md` for pilot gates.
