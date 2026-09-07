# MGC Engineering AI Local v5.8.0

## Field Reliability & Product Lifecycle Intelligence

v5.8 extends the digital thread beyond SOP and series production into controlled field/warranty evidence.

### Added

- Field reliability exposure snapshots with population, censored population, censor mileage and total exposure-km.
- Failure-rate metrics per vehicle population and per million km when exposure data is present.
- Two-parameter Weibull estimate with grouped right-censoring and explicit `INSUFFICIENT_DATA` behavior.
- Extended field claims: mileage, in-service date, market/climate, repair method, NTF/repeat repair and advisory cost breakdown.
- Design FMEA engineering shadow records and Field -> DFMEA review signals.
- Validation-effectiveness review using matching passed V&V and recorded validated mileage.
- Revision-level observed field effectiveness comparison; human confirmation remains mandatory.
- VIN Field Trace through build genealogy -> field claims -> applicable TSB/field actions.
- TSB, field containment and campaign-assessment engineering actions with human approval boundaries.
- Campaign candidate assessment is advisory only; no automatic recall/campaign or safety-defect declaration.
- Repair-effectiveness / NTF patterns and advisory Field Quality Cost.
- Closed/verified field investigations continue into Engineering Knowledge Memory with richer lifecycle metadata.

### Governance

- `causal_claim=false` for field clusters, revision comparisons and investigation associations.
- DMS/Warranty/ERP remain systems of record.
- No customer/driver profiling; market/climate are technical aggregate dimensions.
- Mixed visible/hidden evidence fails closed.
- Core reliability calculations are CPU-only and deterministic.
