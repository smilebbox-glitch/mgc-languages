# Changelog v5.5 — Pilot Operations / SLO / IT Alerts

## User / Chinese learning
- Kept the user-facing section name **«Информация о китайском»**.
- Added **«Как один смысл звучит по-разному»** inside the Putonghua/dialect block.
- Added side-by-side orientation examples for `你好`, `吃饭` and `我不知道`.
- Examples cover selected Putonghua, Cantonese/Yue, Shanghai Wu, Chengdu/Sichuan (Southwestern Mandarin), Hakka, Hokkien/Min and Gan forms/pronunciations.
- Added explicit labels for Pinyin, Jyutping and regional romanization systems.
- Regional examples do **not** use the Mandarin TTS engine. Only validated standard-Mandarin audio is played; regional text is an orientation aid.
- No microphone or voice recording was added.

## Pilot Operations
- Added rolling process-local SLO snapshot:
  - availability percentage;
  - HTTP 5xx/error rate;
  - p50/p95/p99 latency;
  - error-budget burn-rate indicator;
  - explicit internal/non-contractual SLA mode.
- Added recovery-state machine: `healthy`, `degraded`, `recovering`, `unavailable`.
- Added persistent `pilot_alerts` with `open`, `acknowledged`, `resolved` states.
- Added alert conditions for readiness failure, DB latency, 5xx rate, p95 latency, TTS circuit breaker and retention backlog.
- Added Admin alert acknowledgement with audit logging.
- Added aggregated learning-error telemetry by topic, activity kind and language.
- Learning-error telemetry is explicitly a content/UX improvement signal, not an employee HR score.
- IT dashboard now shows SLO, recovery state, active alerts and weak-learning-topic aggregates.
- Prometheus metrics now expose SLO values, recovery state and active alert count.

## Database / lifecycle
- New Alembic head: `a55c0b91d550`.
- New `pilot_alerts` table with acknowledgement/resolution metadata.
- Resolved alerts participate in configurable retention cleanup (`ALERT_RETENTION_DAYS`, default 90).

## Configuration
New environment controls:
- `PILOT_SERVICE_WINDOW`
- `PILOT_SLA_MODE`
- `SLO_WINDOW_MINUTES`
- `SLO_AVAILABILITY_TARGET_PERCENT`
- `SLO_ERROR_RATE_TARGET_PERCENT`
- `SLO_P95_TARGET_MS`
- `ALERT_ERROR_RATE_PERCENT`
- `ALERT_P95_MS`
- `ALERT_DB_LATENCY_MS`
- `ALERT_CLEANUP_BACKLOG`
- `RECOVERY_STABLE_SECONDS`
- `ALERT_RETENTION_DAYS`

## Acceptance / operations package
- Added v5.5 regression test for SLO, recovery, alerts, learning-error telemetry and dialect-comparison content.
- Added v5.5 IT acceptance script with Markdown report output.
- Added Pilot Operations runbook and dialect-comparison content note.
- Pilot image tag: `mgc-languages:5.5-it`.
