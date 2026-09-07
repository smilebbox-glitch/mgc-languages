# v5.6 Vehicle Build & Launch Intelligence — Pilot Acceptance

1. Import two Pilot Build records with distinct VIN/build identifiers.
2. Import genealogy for one complete 100% variant and verify 100% coverage.
3. Remove one expected genealogy item and confirm status becomes RED with an explicit missing part.
4. Link the same failure mode on two builds with the same part/supplier and verify recurrence is surfaced.
5. Configure Safe Launch below minimum inspected population and confirm exit is blocked.
6. Reach required population/clean-build streak with zero defects and verify only `exit_candidate=true`; no automatic exit occurs.
7. Link Build Defect → 8D → ECO and inspect later builds; verify the feedback path is shown with `causal_claim=false`.
8. Repeat with mixed hidden evidence and confirm the build/cross-domain record fails closed.
9. Verify CPU-only operation with AI model services disabled.
10. Run corporate build-host gates: `docker compose build`, `make dockle`, `make acceptance`.
