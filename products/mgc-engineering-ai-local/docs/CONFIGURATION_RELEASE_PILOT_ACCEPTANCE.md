# v5.5 Configuration & Release Assurance — Pilot Acceptance

1. Import/configure one controlled MBOM from the approved manufacturing source and prove EBOM↔MBOM `ALIGNED` for a known variant.
2. Change an MBOM revision or quantity and confirm deterministic `MISMATCH` without LLM use.
3. Leave one variant applicability unresolved and confirm `UNKNOWN` blocks exact 100% configuration.
4. Configure two non-overlapping VIN effectivity ranges and confirm AS-BUILT uses only the rule applicable to the tested VIN/plant/date scope.
5. Import an AS-BUILT revision outside released effectivity and confirm `RED`; link an approved deviation and confirm it becomes explainable `AMBER`, not released equivalence.
6. Create a Change Cut-In with old stock but no disposition/logistics confirmation/target-revision PPAP and confirm all blockers are exposed.
7. Freeze a new v5.5 Release Baseline, modify MBOM/effectivity and confirm Release Drift.
8. Generate Configuration Release Package and verify its SHA-256 fingerprint changes when manufacturing configuration evidence changes.
9. Confirm a row with mixed visible/hidden evidence is completely excluded from assurance output.
10. Confirm human-facing v5.5 endpoints enforce identity and configuration-authority shadow writes require Engineering Admin.
11. Confirm CPU runtime provides the complete deterministic v5.5 feature set without GPU/LLM.
12. Confirm no API call writes to external PLM/PDM, ERP, MES, PLC or production equipment.
