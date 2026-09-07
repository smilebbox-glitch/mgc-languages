# Production Operations Game Day Runbook — v6.0.9

## Purpose

This runbook validates operational recovery on an approved non-production or controlled-pilot environment. **MGC records plans, timestamps, evidence and acceptance results but never injects infrastructure faults itself.** Fault injection is performed by authorized infrastructure operators using approved corporate tooling and change controls.

## Required drills

### postgres-outage
Simulate loss of PostgreSQL connectivity on the approved test environment. Record detection, mitigation, recovery, verification, RTO and RPO evidence. Confirm readiness fails closed during the outage and returns only after schema/data verification.

### redis-outage
Interrupt Redis on the approved environment. Confirm deterministic engineering reads remain bounded by configured readiness policy, workers/queues recover, and no duplicate job execution is accepted without evidence.

### qdrant-outage
Interrupt Qdrant. Confirm optional/local AI and search degradation is explicit, evidence access remains controlled, and recovery restores vector-search availability without altering authoritative engineering facts.

### worker-crash-restart
Stop one Celery worker through approved orchestration. Verify jobs are not silently lost, queue age/alerts behave as designed, worker health returns after restart, and any retry remains idempotent.

### integration-outage
Make one PLM/ERP/MES/QMS integration unavailable. Verify data confidence/freshness decays, reconciliation does not silently remain green, and recovery catches up without duplicate ingest ledger entries.

### expired-tls-certificate
Use a deliberately invalid/expired test certificate at the enterprise edge. Verify clients fail closed, alerting occurs, renewal/reload restores service, and no insecure fallback is enabled.

### oidc-failure
Use an approved invalid issuer/JWKS/audience test. Verify login fails closed without leaking JWT internals and service recovers after identity-provider configuration is restored.

### queue-overload
Generate approved synthetic read/compute load until queue-age warning policy is exceeded. Verify bounded admission/monitoring behavior, no data corruption, and recovery after load removal.

### backup-restore
Perform the documented backup→restore exercise on an isolated target. Verify PostgreSQL, evidence storage and Qdrant snapshot integrity, restore checksums, schema readiness, and measured RTO/RPO.

## Evidence minimum

For each exercise capture: change/ticket reference, operator-approved fault-injection reference, fault time, detection time, recovery time, verification time, RTO, RPO, relevant alert/runbook evidence and result. Do not paste credentials, raw tokens, engineering document contents or personal telemetry into game-day evidence.

## Acceptance semantics

- `rehearsal` can only return `PRECHECK_PASS` or `PRECHECK_FAIL`.
- `controlled` may return `GO`, `CONDITIONAL_GO` or `NO_GO`.
- Missing required drills, RPO breach, critical RTO breach, open critical production incident, or missing required external runtime gate => `NO_GO`.
- A small non-critical RTO miss or open high incident => at most `CONDITIONAL_GO`.
- `GO` remains advisory: `human_go_live_required=true` and `deployment_authorized=false`.

## Required external evidence gates

Docker runtime acceptance, resolved CVE scan, dependency-lock resolution, OIDC negative tests, mTLS negative tests, alert-routing verification and pilot performance profile must all be recorded as PASS for controlled GO.
