# Operations Acceptance — v6.0.9

v6.0.9 converts operational readiness from a checklist into evidence-backed controlled game days. It does not add automotive business scope and does not perform destructive actions.

## Metrics

- **RTO**: fault injection/start → recovered.
- **MTTR**: detected → recovered.
- **RPO**: operator-recorded maximum recoverable data-loss window verified by restore/integration evidence.

Every target and actual value is visible. No AI-generated reliability score is used.

## Decision boundary

A finalized operations acceptance is a recommendation to the corporate Go-Live board. The API always returns `deployment_authorized=false`; production authorization is outside MGC.
