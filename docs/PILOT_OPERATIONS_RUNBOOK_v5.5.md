# MGC Languages v5.5 — Pilot Operations Runbook

## 1. Scope
This runbook is for a controlled internal pilot. It does not declare a contractual SLA or production HA architecture.

## 2. Default pilot SLO
Default environment values:
- availability target: >= 99.0%;
- HTTP 5xx target: <= 1.0%;
- p95 API latency target: <= 2000 ms;
- rolling window: 60 minutes;
- service window label: `business-hours`.

The in-app rolling SLO is **process-local** and resets when the app process restarts. For more than one app instance, central Prometheus/SIEM aggregation is the authoritative view.

## 3. Recovery state machine
`healthy`
: Readiness checks pass and offline TTS is available.

`degraded`
: Core learning remains available but a non-critical dependency such as offline TTS is degraded; browser speech fallback is expected.

`unavailable`
: Readiness policy fails because a critical dependency/configuration is not safe for traffic, such as DB/schema failure.

`recovering`
: A previously degraded/unavailable instance has passed current checks but must remain stable for `RECOVERY_STABLE_SECONDS` before returning to `healthy`.

## 4. Alert model
Persistent alert states:
- `open` — condition is currently active and not acknowledged;
- `acknowledged` — IT has seen it; this does **not** mean resolved;
- `resolved` — the condition is no longer active.

Default alert conditions:
- readiness not ready;
- DB readiness latency above threshold;
- rolling 5xx rate above threshold;
- rolling p95 above threshold;
- TTS circuit breaker open;
- retention-cleanup backlog above threshold.

Admin acknowledgement is audit-logged.

## 5. Learning-error telemetry
`GET /api/admin/learning-error-telemetry`

Purpose:
- identify confusing content;
- find weak topics across the pilot;
- prioritize vocabulary/exercise redesign;
- compare current accuracy with the previous equal-length window.

It is **not** an HR score and should not be used alone for employee performance decisions.

## 6. Dashboard workflow
1. Open Admin → `IT · Pilot Operations`.
2. Confirm readiness and recovery state.
3. Check active alerts.
4. Review rolling SLO and sample count.
5. Acknowledge alerts that are under investigation.
6. Investigate DB/TTS/HTTP operational events.
7. Preview retention cleanup before executing it.
8. Review aggregated learning-error telemetry separately from infrastructure health.

## 7. Prometheus metrics added in v5.5
- `mgc_slo_availability_percent`
- `mgc_slo_error_rate_percent`
- `mgc_slo_p95_ms`
- `mgc_slo_samples`
- `mgc_recovery_state`
- `mgc_pilot_alerts_open`

Existing HTTP, DB, operational-event and TTS metrics remain available.

## 8. Incident response examples
### PostgreSQL unavailable
Expected:
- `/health/live` remains 200;
- `/health/ready` becomes 503;
- normal DB-backed API returns controlled retryable 503;
- recovery state becomes `unavailable`;
- no DB credentials/internal exception are shown to the user.

After DB restoration:
- schema/readiness checks pass;
- state becomes `recovering`;
- after the configured stable period it becomes `healthy`.

### Offline TTS unavailable
Expected:
- core learning remains usable;
- recovery state becomes `degraded`;
- browser SpeechSynthesis is used where available;
- TTS circuit alert may open;
- no microphone permission is requested.

## 9. Multi-instance boundary
The v5.5 in-app SLO window is intentionally lightweight for a controlled pilot. If IT runs multiple app replicas:
- aggregate `/metrics` in Prometheus;
- alert centrally from aggregated data;
- treat the per-instance Admin SLO as diagnostic only;
- keep PostgreSQL migration advisory locking enabled.

## 10. Exit criteria for controlled pilot operations
Recommended evidence before wider rollout:
- real corporate OIDC tested;
- TLS/secure cookies enabled;
- 7–14 days of SLO data captured centrally;
- backup and isolated restore rehearsal completed;
- DB/TTS degradation drills documented;
- alert thresholds tuned from observed baseline;
- no unresolved critical security findings;
- content owner reviews regional Chinese examples.
