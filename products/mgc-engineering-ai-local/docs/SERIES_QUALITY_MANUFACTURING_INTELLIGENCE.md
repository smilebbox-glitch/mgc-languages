# Series Quality & Manufacturing Intelligence — v5.7

## Purpose

v5.7 extends the automotive Engineering Digital Thread beyond Pilot/Safe Launch into controlled series observation. The module is an engineering intelligence/evidence layer. MES, QMS, SPC, ERP and warranty systems remain authoritative and no machine, line, inspection, shipment or financial transaction is controlled by MGC.

## Controlled data model

### SeriesQualityObservation
Aggregated factual production/quality bucket with project/area/plant/line/station/operation/shift/variant/part/revision/supplier-lot context, produced/inspected/defect counts, in-process detection, escapes and advisory COPQ components.

### ProcessCapabilityRecord
Evidence-backed Cp/Cpk/Pp/Ppk snapshot for one characteristic, optional process asset and process location. Cpk bands are descriptive: `<1.0 RED`, `1.0–<1.33 AMBER`, `>=1.33 GREEN`; they do not approve the process.

### SeriesContainmentCase
Human-controlled containment evidence including suspect population, inspected quantity, defects and actions. MGC never issues stop-ship, quarantine or release commands.

### FieldQualityClaim
Read-only/advisory warranty/field claim shadow record for engineering traceability. Claims can become ACL-safe historical cases in Engineering Knowledge Memory.

## Deterministic intelligence

- Series Health from visible observation/capability/supplier/containment evidence.
- Change-point signal uses a simple explainable two-window defect-rate ratio; it is not presented as causal proof or formal SPC replacement.
- Supplier-lot, shift and station signals compare observed rates with the accessible baseline and always return `causal_claim=false`.
- Suspect VIN population is resolved from actual VehicleBuild + BuildGenealogyItem records and explicit filters.
- PFMEA ↔ Control Plan ↔ actual-defect loop can request human PFMEA review when series evidence contradicts a low occurrence assumption or a control link is missing.
- Control effectiveness compares known in-process detections with recorded downstream escapes.
- Tooling/calibration signals use ProcessAsset due dates plus linked capability/defect facts; they never control equipment.
- COPQ is advisory only; ERP/Finance remains system of record.

## ACL invariant

Every cross-domain row is filtered by Project + Manufacturing Area + Document evidence ACL. Mixed visible/hidden evidence fails closed as a whole object. VIN/lot/field views cannot be used to infer hidden documents, parts or protected manufacturing-area data.

## CPU operation

All core calculations are SQL + deterministic Python and require no GPU or LLM. Ask Series Intelligence is deterministic and returns facts/signals rather than generated root-cause claims.

## Authority boundary

`correlation_only=true` and `causal_claim=false` are intentional. Root cause, PFMEA update, containment status, process release, operator/supplier accountability and production release remain human/corporate-process decisions.
