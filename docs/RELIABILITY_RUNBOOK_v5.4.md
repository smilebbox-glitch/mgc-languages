# MGC Languages v5.4 — Reliability Runbook

## Failure domains

### PostgreSQL unavailable
Expected behavior: liveness stays up, readiness fails, DB-backed API responds with controlled retryable 503. The DB exception path logs the request ID and increments an in-memory counter; it intentionally does **not** attempt to persist the DB-outage event to PostgreSQL.

### PostgreSQL slow
`/health/ready` measures query latency. If latency exceeds `DB_READY_MAX_LATENCY_MS`, readiness fails even if `SELECT 1` eventually succeeds. Tune this threshold only from observed pilot latency and corporate platform SLOs.

### Offline TTS unavailable
Core learning stays ready. Pronunciation endpoint returns 503 and frontend falls back to browser SpeechSynthesis. Repeated TTS engine failures open the local circuit breaker to avoid spawning failing subprocesses repeatedly.

### Maintenance failure
The maintenance sidecar logs failure and retries on the next interval. It never owns user-facing traffic. Cleanup is bounded to expired sessions and configured retention categories.

## Operational signals
- `/health/live` — process liveness only.
- `/health/ready` — DB/schema/config readiness.
- `/metrics` — protected Prometheus metrics.
- `/api/admin/it-dashboard` — Admin summary.
- `/api/admin/operational-events` — persistent events while DB is available.
- structured application logs with `X-Request-ID` correlation.

## Default pilot retention
- audit: 180 days;
- operational events: 30 days;
- nudges: 60 days;
- expired sessions: removed on maintenance cycle/login cleanup.

These are pilot defaults, not a legal/HR retention policy.
