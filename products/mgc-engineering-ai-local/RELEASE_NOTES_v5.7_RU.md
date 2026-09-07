# MGC Engineering AI Local v5.7.0

## Series Quality & Manufacturing Intelligence

v5.7 продолжает цепочку после Vehicle Build & Launch Intelligence и добавляет evidence-based наблюдение серийного производства после SOP. MES/QMS/SPC/ERP/Warranty остаются authoritative systems; MGC не управляет оборудованием, линией, shipment, запасами или финансовыми транзакциями.

### Series Production Health

- aggregated series quality observations по project / area / plant / line / station / operation / shift / variant;
- produced / inspected / defect counts;
- defect rate и in-process detection / downstream escape;
- compact Series Health band без нового глобального dashboard.

### Process Capability

- Cp / Cpk / Pp / Ppk snapshots;
- LSL / USL / mean / sigma / sample size;
- explainable RED / AMBER / GREEN capability band;
- trend `DEGRADING / STABLE / IMPROVING`;
- optional ProcessAsset linkage for tooling/gauge context.

### Quality change-point signals

- deterministic two-window defect-rate comparison;
- rate ratio, before/after rate and signal timestamp;
- nearby changes in supplier lot / part revision / station / shift shown only as associations;
- always `correlation_only=true`, `causal_claim=false`.

### Suspect VIN Population

Read-only population builder over actual v5.6 genealogy with filters:

- part / revision;
- supplier / supplier lot;
- plant;
- vehicle variant;
- build date window.

No VIN is inferred without visible Build + Genealogy evidence.

### Containment

- human-controlled containment case;
- suspect VIN population;
- inspected / defects / remaining quantity;
- actions and linked 8D;
- no automatic stop-ship, quarantine, release or QMS status change.

### PFMEA ↔ Control Plan ↔ Actual Defect

- actual series defects can be compared with PFMEA failure mode/occurrence;
- linked Control Plan items are shown;
- low occurrence assumption contradicted by series facts produces `PFMEA REVIEW REQUIRED`;
- PFMEA itself is never changed automatically.

### Control effectiveness / Escape

- known in-process detections;
- downstream escapes;
- detection effectiveness and escape rate.

### Supplier / Station / Shift intelligence

- supplier-lot rate outliers;
- station and shift concentration signals;
- all results are investigation signals only and are never used as operator/supplier blame or causal proof.

### Tooling / Calibration

- expired calibration / overdue maintenance signals;
- post-expiry capability sample count;
- Cpk and related-defect context;
- no machine-control commands.

### Field / Warranty and Engineering Memory

- field claims linked to VIN/part/revision/supplier/8D;
- repeated field issue clusters;
- ACL-safe Field → Engineering Knowledge Memory cases;
- no automatic warranty root cause.

### Advisory COPQ

- scrap;
- rework;
- containment;
- warranty estimate;
- totals by currency.

ERP/Finance remains system of record.

### Ask Series Intelligence

CPU-only deterministic answers over series signals. The assistant can explain observed facts but cannot declare root cause.

## Security / deployment

- Project + Manufacturing Area + Document ACL remain fail-closed;
- mixed visible/hidden evidence hides the complete series object;
- authority-shadow import endpoints require Engineering Admin;
- no new global UI navigation item;
- CPU-first core; GPU/LLM not required for Series Intelligence.

Schema upgrade wrapper: `ensure_v57_schema()`.
