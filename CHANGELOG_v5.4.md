# Changelog v5.4 — Pilot Reliability / IT Operations

## User-facing
- Renamed the Chinese foundations block from **«Китайский без страха»** to **«Информация о китайском»**.
- Kept Pinyin, tones, Tone Lab, initials/finals, Putonghua/dialect overview, context explanations, Russian reading hints and playback-only pronunciation.
- Voice recording remains disabled; `Permissions-Policy: microphone=()` remains enforced.
- Added a clear service-degraded banner when the API reports `database_unavailable` instead of leaving the UI with an unexplained error.

## Database resilience
- PostgreSQL client connect timeout and statement timeout are now configurable.
- Readiness measures DB latency and can fail when it exceeds `DB_READY_MAX_LATENCY_MS`.
- SQLAlchemy database failures return a controlled retryable `503` without exposing DB internals.
- DB outage telemetry uses structured logs + in-memory counters so the failure handler does not attempt to write back to the unavailable database.
- New Alembic head `f54c0a91b723` adds `operational_events`.

## Operational telemetry
- Persistent operational events for TTS fallback/failure and HTTP 5xx paths while DB is available.
- `/api/admin/it-dashboard` exposes readiness, schema, DB latency/pool, TTS circuit state, HTTP errors, recent operational events and maintenance preview.
- `/api/admin/operational-events` provides filtered Admin event access.
- Prometheus metrics add DB-backed operational-event gauges and process-local DB/HTTP failure counters.

## Retention / maintenance
- Explicit retention controls for audit logs, operational events and learning nudges.
- Expired login sessions are cleaned proactively.
- Added `scripts/maintenance_cleanup.py` and an internal maintenance service in pilot Compose.
- Admin can dry-run or execute cleanup through an audited endpoint.

## Pilot topology / checks
- Pilot app image tag: `mgc-languages:5.4-it`.
- Packaged Alembic head: `f54c0a91b723`.
- Added v5.4 reliability/failure-mode tests, IT acceptance script and safe reliability observation drill.
