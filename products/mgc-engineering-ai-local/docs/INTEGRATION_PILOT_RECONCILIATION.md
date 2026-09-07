# v6.0.3 — Real Integration Pilot & Data Reconciliation

This layer is intentionally read-only. PLM/PDM, ERP, MES and QMS remain authoritative in their own domains.

## Recommended pilot roles

| Source | Reconciliation role | Typical objects |
|---|---|---|
| PLM/PDM | `ebom` | EBOM rows / released part revisions |
| ERP | `mbom` | MBOM rows / supplier planning |
| MES | `genealogy` | VIN component genealogy |
| QMS | `defects` | defect / non-conformance records |

Configure each integration with `config.reconciliation.role` and, where a connector is project-specific, `config.reconciliation.project_code`.

## Mapping policy

Exact canonical identifiers (`part_number`, VIN, supplier code) do not require mapping rows. Aliases require an explicit `IntegrationEntityMapping` confirmed by an Engineering AI administrator. A mapping becomes stale when its source object fingerprint changes; a stale mapping is not used to make reconciliation green.

## Reconciliation gates

1. PLM EBOM ↔ ERP MBOM: missing/extra/replacement/revision/quantity/unit/supplier drift.
2. MES genealogy ↔ release baseline/effectivity: VIN-level observed part revision against provable released revision.
3. QMS ↔ Part/VIN/Supplier: linkage coverage; no inferred link is persisted automatically.
4. Source-of-truth conflicts: multiple explicit authorities or incompatible revision claims are surfaced; no winner is selected automatically.
5. Integration SLO: freshness compliance, recent sync success, quarantine backlog.
6. Pilot acceptance: deterministic criteria, never an automatic production release.

## Suggested controlled-pilot thresholds

- mapping coverage ≥ 95%
- freshness compliance ≥ 95%
- recent sync success ≥ 95%
- no quarantined events
- no unresolved authority conflict
- required source roles present

Thresholds are pilot policy, not engineering truth. Human go-live approval remains mandatory.
