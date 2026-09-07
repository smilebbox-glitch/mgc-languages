# Engineering Traceability & Release Baseline — v4.9

## Purpose

v4.9 freezes an immutable engineering snapshot at Design Freeze, Release, SOP or audit checkpoints and adds a human-readable BOM version comparison.

A baseline is evidence, not an automatic release approval. It stores a SHA-256 fingerprint over the captured snapshot and the source-document hashes used to build it.

## Release baseline content

A baseline can capture:

- project and optional vehicle variant;
- exact visible document IDs, filenames, revisions and SHA-256 hashes;
- part revisions;
- BOM rows and BOM fingerprint;
- requirements and V&V records;
- PPAP and supplier/localization snapshot;
- ECR/ECO state;
- Design Review state;
- open critical validation issues;
- configuration UNKNOWNs and other freeze warnings.

`release_candidate=false` means the snapshot was frozen successfully but still contains an engineering gap. It is not an automatic reject or approval.

## Immutability

There is no baseline update endpoint. A later engineering state produces a new baseline with a new code and fingerprint.

If a user later loses access to any source document that contributed to a baseline, the baseline fails closed for that user. Project membership does not grant access to hidden baseline evidence.

## BOM Version Compare

BOM versions are identified by the immutable BOM source documents already stored by the platform. The comparison reports only changes:

- added part;
- removed part;
- replacement at the same position;
- moved part / changed BOM position;
- child revision change;
- quantity / unit change;
- description change;
- supplier-code/name change when present in the BOM;
- unit-cost / currency change when present in the BOM;
- deterministic BOM cost delta when both versions have complete prices in one currency.

The comparison is deterministic. It does not use an LLM to infer BOM changes.

## Typical workflow

1. Upload BOM Rev A and BOM Rev B.
2. Open Project or Part.
3. Open **Релиз и версии BOM** / **Сравнить версии BOM**.
4. Select left and right BOM versions.
5. Review added/removed/replaced/moved/changed lines and the optional cost delta.
6. At Design Freeze or SOP, freeze a baseline for the selected vehicle variant.
7. Later compare two baselines to see both BOM and document-level drift.

## Authority boundary

MGC Engineering AI remains an engineering intelligence/evidence layer. PLM/PDM is still authoritative for product structure and ERP is still authoritative for financial/production transactions. Human release approval remains mandatory.

## v5.5 configuration-authority extension

Newly frozen release baselines use `mgc-release-baseline-v3`. In addition to the v5.1/v5.4 engineering snapshot they can contain ACL-filtered manufacturing BOM, configuration effectivity, change cut-in and part-supersession evidence. Configuration & Release Assurance uses these fields for semantic release-drift detection. The volatile `captured_at` field is ignored for drift so time alone cannot create a false change.
