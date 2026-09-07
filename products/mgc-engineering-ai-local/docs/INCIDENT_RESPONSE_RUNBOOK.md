# Production Incident Response Runbook — v6.0.8

## 1. Confirm scope

1. Check `/api/v1/health/live` and `/api/v1/health/ready`.
2. As Engineering Admin, open `/api/v1/operations/summary`.
3. Record an incident if a user-facing or evidence-integrity impact exists.
4. Do not paste passwords, tokens, raw engineering documents or customer/VIN histories into the incident evidence field.

## 2. Identify layer

Use the bounded signals:

- database/evidence-storage readiness;
- Redis queue depth and oldest queued job age;
- Qdrant/Neo4j/object-store readiness when enabled;
- integration freshness/data confidence;
- API error/latency metrics in Prometheus/OTel.

Do not infer engineering root cause from infrastructure telemetry.

## 3. Collect support evidence

Export the privacy-safe support bundle from `/api/v1/operations/support-bundle`. Preserve its SHA-256. If deeper logs are required, collect them through the approved corporate logging platform with the incident ticket and access policy; do not extend the MGC bundle to include raw logs by default.

## 4. Recover using approved runbooks

- Database/storage failure: follow `BACKUP_RESTORE_DR.md`.
- Integration failure: follow `INTEGRATION_HARDENING_DATA_CONFIDENCE.md` and quarantine/replay workflow.
- Capacity/latency issue: follow `PERFORMANCE_SCALE_CERTIFICATION.md`.
- Identity/TLS issue: follow `ENTERPRISE_SECURITY_DEPLOYMENT.md`.

No automatic destructive repair is performed by MGC.

## 5. Resolution

An incident can move to `resolved` only with a resolution summary. Record post-recovery verification evidence and keep the operational incident separate from engineering/QMS defects.

## 6. Post-incident review

Review:

- SLO error-budget burn;
- whether alerts were actionable;
- queue/integration lag;
- recovery time;
- whether runbooks were sufficient;
- whether a new preventive engineering/IT action is required.
