# Vehicle Build & Launch Intelligence — v5.6

## Purpose
v5.6 closes the engineering loop at individual vehicle/build level for Pilot Build, pre-series and Safe Launch. It is an engineering intelligence/evidence layer: MES, ERP and QMS remain authoritative systems and no production command is issued.

## Controlled data model
- `VehicleBuild`: VIN/build identifier, variant, plant/line, build type, timestamps and optional release baseline.
- `BuildGenealogyItem`: installed part/revision, supplier, lot/serial and source-system provenance.
- `BuildDefectLink`: link from a build to the existing `ProcessDefect`; the defect itself is not duplicated.
- `SafeLaunchControl`: inspected population, defect count, clean-build streak and human-controlled exit status.

## Main workspace
The Project Workspace card exposes:
1. latest builds and build quality status;
2. selected VIN genealogy and expected-vs-observed coverage;
3. recurring defect clusters by part / supplier / variant;
4. Safe Launch exit candidates and explicit gaps;
5. explainable `Build → Defect → 8D → ECO → later build` feedback paths.

## Safe Launch governance
`exit_candidate=true` is deterministic evidence only. It requires the configured inspected quantity, zero recorded Safe Launch defects and the configured clean-build streak. Moving a control to `exited` requires Engineering Admin and the server rejects exit when criteria are not met. Human quality/engineering release authority remains mandatory.

## Causality boundary
A defect disappearing after an ECO is not proof that the ECO caused the improvement. Feedback paths always expose `causal_claim=false`; they show chronology and traceability for engineer review.

## ACL boundary
Project / Manufacturing Area / Document ACL is applied before build, genealogy, defect-link and Safe Launch aggregation. A record with mixed visible/hidden evidence fails closed.

## CPU / local operation
The core v5.6 calculations are SQL + deterministic Python. No GPU or LLM is required for genealogy coverage, recurrence, Safe Launch exit checks or feedback-loop status.
