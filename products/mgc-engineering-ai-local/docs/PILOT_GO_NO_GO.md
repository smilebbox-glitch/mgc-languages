# Formal Pilot Gate — v6.0.6

## GO
All critical and conditional checks pass, integration reconciliation is `READY_FOR_CONTROLLED_PILOT`, enterprise security posture is PASS and every required external runtime gate has evidence with status PASS.

## CONDITIONAL_GO
All critical checks pass but one or more non-critical KPI targets (task-time reduction, usability or aggregate UX error rate) miss their target. Conditions and owners must be agreed by the human pilot board before expansion.

## NO_GO
Any critical failure: missing required role/scenario, scenario failure/block, incomplete required evidence, high/critical blocker, reconciliation not ready, security posture not PASS, or missing/failed runtime security/DR/performance gate.

## External evidence gates
- `docker_runtime_acceptance`
- `cve_scan`
- `oidc_negative_tests`
- `backup_restore_drill`
- `performance_pilot`

A local packaging test cannot substitute for these corporate runtime gates.
