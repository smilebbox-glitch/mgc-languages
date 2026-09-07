# v6.0.2 Integration Hardening — Pilot Acceptance

The pilot is not accepted merely because an adapter returns HTTP 200. Verify each production-like connector against these gates.

## Contract / provenance

- source domain and authoritative owner are documented;
- unique external ID is stable across repeated syncs;
- revision/checksum/source timestamp semantics are documented;
- required fields are explicitly declared;
- source timestamp timezone is unambiguous;
- imported evidence records source system, external ID and ingest-event ID;
- source metadata cannot override MGC provenance or ACL.

## Idempotency

- repeat sync with unchanged source creates no duplicate controlled document;
- source revision/checksum change creates immutable history;
- when the source has no revision/checksum/timestamp, changed bytes are still detected by payload SHA-256;
- pagination cursor and source checkpoint are tested independently.

## Freshness / confidence

- expected freshness SLA is configured for sources where freshness matters;
- fresh, aging, stale and unknown conditions are exercised;
- completeness drops when a required source field is absent;
- administrators can see component scores instead of only an opaque overall band;
- stale-but-schema-valid data remains visible with explicit confidence rather than being deleted.

## Quarantine / replay

- malformed contract record is not indexed into the Digital Thread;
- immutable quarantined bytes are checksum-identifiable;
- repeated polling does not endlessly reprocess the same DLQ item;
- corrected mapping/contract can explicitly replay a quarantined payload;
- replay revalidates against the current contract and never bypasses it;
- an event without local replay payload clearly requires source resynchronization.

## Security

- connector credentials are environment references, not API-stored plaintext;
- source ACL does not widen document access;
- identical bytes from two systems with different ACL remain different document records;
- quarantine paths and connector secrets are not exposed through user APIs;
- integration administration endpoints are Engineering-Admin guarded.

## Real pilot evidence

For each PLM/PDM/ERP/MES/QMS connector, capture:

- sample source contract;
- 100+ repeated records across at least two sync cycles;
- one deliberate source update;
- one deliberate malformed record / DLQ replay;
- measured source-to-MGC freshness;
- reconciliation count against authoritative source;
- operator sign-off from IT integration owner and engineering data owner.
