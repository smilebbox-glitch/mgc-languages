# v5.8 Field Reliability Pilot Acceptance

1. Import one field exposure with population, censored count and censor mileage; confirm failure-rate and Weibull output is deterministic.
2. Remove censoring or reduce mileage-bearing failures below three; confirm `INSUFFICIENT_DATA`.
3. Link field failures to a low-occurrence DFMEA item; confirm `DFMEA_REVIEW_REQUIRED` without automatic DFMEA modification.
4. Record validation mileage below observed field failure mileage; confirm `VALIDATION_COVERAGE_GAP`.
5. Create a TSB scoped to part/revision/supplier and confirm VIN applicability from actual genealogy.
6. Confirm campaign candidate output is advisory and never becomes an automatic recall/service-campaign decision.
7. Confirm NTF/repeat-repair analysis is a technical pattern and does not rank dealers/operators.
8. Use one mixed visible/hidden evidence record; confirm the whole object fails closed.
9. Close a field claim with `metadata.verified_outcome=true`; confirm it can enter Engineering Knowledge Memory as controlled historical evidence.
10. Run CPU-only deployment and verify field intelligence functions without LLM/VLM availability.
