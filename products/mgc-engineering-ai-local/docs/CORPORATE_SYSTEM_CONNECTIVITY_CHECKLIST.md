# PLM / ERP / MES / QMS Connectivity Checklist — v6.1.0

For every source system:

1. Name the corporate data owner and technical owner.
2. Define read-only endpoint/gateway and least-privilege service identity.
3. Fix object IDs, revision rules, source timestamp and checksum/version semantics.
4. Configure freshness SLA and required fields.
5. Test idempotency, quarantine/replay and source outage behavior.
6. Reconcile aliases in the Canonical Mapping Registry; no automatic alias confirmation.
7. Run PLM EBOM↔ERP MBOM, MES↔released configuration and QMS linkage checks where applicable.
8. Require `READY_FOR_CONTROLLED_PILOT` from v6.0.3 reconciliation.
9. Preserve source-system authority; no write-back is introduced by v6.1.0.
