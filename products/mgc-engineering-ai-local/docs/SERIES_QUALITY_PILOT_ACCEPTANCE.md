# v5.7 Series Quality & Manufacturing Intelligence — Pilot Acceptance

## Functional acceptance

1. Import at least four time-ordered quality observations and confirm a >2× sustained rate step is surfaced as a change-point signal with `causal_claim=false`.
2. Import two capability snapshots for one characteristic and confirm Cpk degradation and RED/AMBER/GREEN bands are explainable.
3. Build a suspect population from part + supplier + lot and verify returned VINs match actual genealogy only.
4. Create a containment record and verify inspected/remaining/defect progress without any MES/QMS write-back.
5. Link PFMEA/Control Plan to a process operation and verify actual series defects can request human PFMEA review.
6. Import multiple supplier lots and confirm an anomalous lot is surfaced as an investigation signal, not a supplier root-cause claim.
7. Use an expired ProcessAsset calibration date and post-expiry capability record; verify the review signal and affected sample count.
8. Import field claims and confirm recurrence/COPQ view plus Engineering Memory availability under the same ACL.
9. Confirm mixed visible/hidden evidence fails closed for series observations, capability, containment and field claims.
10. Confirm Ask Series Intelligence remains deterministic and explicitly requires human investigation.

## Security / governance acceptance

- Verify Project, Manufacturing Area and Document ACL with real corporate groups.
- Verify standard users cannot import authority-shadow series/capability/containment/field records.
- Verify no endpoint sends control commands to PLC/MES/QMS/SPC/ERP.
- Verify root-cause/containment/PFMEA/process-release status remains human-controlled.

## Build-host gate

```bash
docker compose build
make dockle
make acceptance
```
