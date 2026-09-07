# MGC Languages v5.7.1 — Security / Data Integrity / Observability & Recovery

Unified English + Chinese corporate language-learning platform for automotive teams. v5.7.1 is a compatible patch on top of v5.7: it keeps RLS, governed terminology, audit chaining and adaptive SRS, then adds privacy-safe database timing telemetry, PostgreSQL pool saturation, measurable backup/restore evidence, pilot RPO/RTO visibility and an internal scheduled backup worker.

## What a user gets
- English + Chinese under one account.
- Professional automotive vocabulary, tests, scenarios, SRS-style review, games and XP help economy.
- Chinese **«Информация о китайском»** module: Pinyin, tones, context, initials/finals, tone changes and starter technical words.
- **Tone Lab**: short ear training for the four main tones with immediate simple feedback.
- New **«Путунхуа и диалекты»** block:
  - what 普通话 means and why it is the practical standard for cross-regional work;
  - why Putonghua is not identical to everyday Beijing speech;
  - why there is no single exact count of local dialects;
  - the 10 major dialect groups used in the Ministry of Education overview;
  - simple examples: Sichuanese as Southwestern Mandarin, Cantonese as Yue, Shanghainese as Wu;
  - **side-by-side pronunciation comparisons** for `你好`, `吃饭` and `我不知道`: Putonghua versus selected Cantonese, Shanghai Wu, Chengdu/Sichuan, Hakka, Hokkien and Gan examples;
  - clear labels for Pinyin vs Jyutping vs regional romanization and a reminder that tone numbers are notation, not spoken digits;
  - accent vs local variety explained in plain language;
  - workplace phrase `请说普通话，可以吗？` with audio.
- Pinyin can be shown or hidden; approximate Russian reading can be hidden separately.
- Every term can be played at normal or slow speed.
- **No microphone, no voice recording, no pronunciation capture.** This release is playback-only.

## Pronunciation architecture
Primary pilot path:

`Browser → POST /api/pronunciation/audio → local eSpeak NG → WAV`

Fallback:

`Browser → SpeechSynthesis (zh-CN / en-US)`

v5.7 uses POST for pronunciation. In the pilot profile the legacy GET endpoint is disabled entirely, so normal learning text is not placed in pronunciation URLs/reverse-proxy access logs. Developer mode can still enable legacy GET explicitly for migration testing.

### TTS resilience
- bounded server-side concurrency;
- configurable synthesis timeout;
- circuit breaker after repeated engine failures;
- short-lived TTS health cache instead of permanent process-lifetime health state;
- bounded local WAV cache with size and TTL limits;
- browser fallback if server audio is unhealthy;
- Prometheus metrics for TTS successes, failures, disk-cache hits and circuit state.

The pilot Compose profile stores the TTS cache under `/tmp` on container tmpfs. It is therefore **ephemeral** and disappears when the app container is replaced. Cache filenames contain hashes, not learning phrases.

## Developer start
```bash
cp .env.example .env
docker compose build
docker compose up -d
```
Open `http://localhost:8080`.

## IT pilot start
```bash
cp .env.pilot.example .env.pilot
# Replace every CHANGE_ME value.
set -a; . ./.env.pilot; set +a
python scripts/pilot_preflight.py
python scripts/oidc_config_check.py

docker compose --env-file .env.pilot -f docker-compose.pilot.yml build
docker compose --env-file .env.pilot -f docker-compose.pilot.yml up -d

MGC_BASE_URL=http://localhost:8080 python scripts/container_smoke.py
MGC_BASE_URL=http://localhost:8080 python scripts/it_acceptance_v571.py --report docs/IT_ACCEPTANCE_REPORT_v5.7.1.md
# On the real PostgreSQL pilot DB:
python scripts/postgres_rls_check.py
bash scripts/pitr_preflight.sh
```

### Pilot architecture
`Browser / corporate ingress → Nginx → FastAPI app → PostgreSQL`

`Internal maintenance sidecar → PostgreSQL`

Only Nginx publishes a host port. App, PostgreSQL and the maintenance sidecar live on an internal Docker network. The app and maintenance process run read-only/non-root with Linux capabilities dropped. PostgreSQL is persistent. The bounded TTS cache is intentionally ephemeral tmpfs and is not a persistent volume.

### Authentication / RBAC
- `AUTH_MODE=local` — technical sandbox.
- `AUTH_MODE=oidc` — corporate OIDC target.
- User / Manager / Editor / Admin roles.
- Manager analytics are restricted to the Manager's own `department`.
- OIDC department claim name is configurable with `OIDC_DEPARTMENT_CLAIM`.
- Self-registration is disabled by default in the pilot example.

### Security / operations baseline
- Alembic schema baseline and PostgreSQL-first pilot.
- PostgreSQL advisory lock serializes startup Alembic migrations so simultaneous app starts do not race schema changes.
- **Schema-head readiness gate:** stale/missing migrations return `503 not_ready` instead of advertising an incompatible app instance as healthy.
- Configurable pilot policy gates can require OIDC, disabled registration, protected metrics and Secure cookies after corporate TLS is connected.
- CSRF protection for cookie-authenticated mutations.
- `Permissions-Policy: microphone=()` — voice recording is explicitly prohibited.
- Pronunciation POST body keeps learning text out of new-client URLs.
- Configurable session TTL and cookie security.
- Trusted Host / explicit CORS controls.
- CSP, HSTS when Secure cookies are enabled, anti-clickjacking and no-sniff headers.
- Sandbox rate limiting for login/import/game/XP/TTS abuse paths.
- Structured request logs with request IDs.
- Admin audit trail and system summary.
- Prometheus-compatible `/metrics` endpoint with bearer-token option.
- PostgreSQL pool configuration.
- Backup/restore scripts with checksums and retention.
- Pilot telemetry including activity, practice accuracy, department distribution and TTS health/cache.
- Controlled DB-unavailable response: retryable `503`, no DB internals, request-ID correlation.
- DB connect/statement timeouts and DB-latency readiness threshold.
- Persistent operational events when DB is available plus in-memory counters/logs for DB-outage paths.
- Internal maintenance sidecar for expired sessions and configured retention cleanup.
- Admin **IT · Pilot Operations** dashboard with readiness/schema/DB/TTS/error/maintenance signals.
- Rolling process-local pilot SLO: availability, 5xx error rate and p95 latency.
- Recovery states: `healthy → degraded → recovering → unavailable`.
- Persistent pilot alerts with Admin acknowledgement and automatic resolution when the condition clears.
- Aggregated learning-error telemetry by topic/activity/language; explicitly not an HR performance rating.
- For multi-instance rollout, Prometheus/SIEM aggregation remains the source of truth; the in-app rolling SLO window is per app process.
- **PostgreSQL FORCE RLS** on user-owned learning data; application RBAC remains the first authorization layer.
- The pilot application DB role must be non-superuser and must not have `BYPASSRLS`; `scripts/postgres_rls_check.py` verifies this on real PostgreSQL.
- Custom terminology has provenance, immutable revision history, Editor review and Admin approval/reject/rollback.
- Audit events are SHA-256 hash chained and retention advances an anchor; this is tamper-evident, not a substitute for off-host SIEM/WORM retention.
- Adaptive SRS persists due dates, repetitions, lapses, intervals and ease factor independently of XP.
- Question-quality telemetry stores correctness/timing plus a hash of the selected answer, not raw selected-answer text.
- OpenTelemetry FastAPI/SQLAlchemy tracing is optional (`OTEL_ENABLED`) and failure to configure/export traces does not block application startup.
- Grafana dashboard, Prometheus alert templates and an OTLP Collector example are included under `deploy/observability/`.
- PostgreSQL logical backups remain available; v5.7 adds WAL/PITR rehearsal configuration and base-backup tooling. Production requires off-host encrypted backup/WAL durability.

## v5.5 pilot SLO / alert model
Default targets are internal **pilot objectives**, not a contractual SLA:
- availability: `>= 99.0%` in the rolling pilot window;
- HTTP 5xx rate: `<= 1.0%`;
- p95 API latency: `<= 2000 ms`;
- alert thresholds default to 2% 5xx rate, 3000 ms p95 and 1000 ms DB readiness latency.

All targets are environment-driven. `PILOT_SLA_MODE=internal-non-contractual` is intentionally explicit so the UI does not present a pilot objective as a legal service commitment. The built-in rolling window is process-local and resets when an app process restarts. For replicated deployment, aggregate exported Prometheus metrics centrally.

## Health / operations endpoints
- `GET /health/live`
- `GET /health/ready`
- `GET /api/pronunciation/status` (authenticated)
- `GET /api/admin/pilot-telemetry` (Admin)
- `GET /api/admin/system/summary` (Admin)
- `GET /api/admin/it-dashboard` (Admin)
- `GET /api/admin/database/telemetry` (Admin)
- `GET /api/admin/recovery/evidence` (Admin)
- `GET /api/admin/slo` (Admin)
- `GET /api/admin/alerts` (Admin)
- `PATCH /api/admin/alerts/{id}/ack` (Admin)
- `GET /api/admin/learning-error-telemetry` (Admin)
- `GET /api/admin/operational-events` (Admin)
- `POST /api/admin/maintenance/cleanup` (Admin)
- `GET /metrics`

## Release checks
Static/schema checks:
```bash
bash scripts/static_preflight.sh
```

Regression is intentionally split into independent CI shards so TTS/TestClient resources cannot accumulate across the entire suite:
```bash
python scripts/run_release_tests.py --shard base --timeout 75
python scripts/run_release_tests.py --shard pronunciation --timeout 75
python scripts/run_release_tests.py --shard putonghua --timeout 75
python scripts/run_release_tests.py --shard reliability --timeout 75
python scripts/run_release_tests.py --shard ops --timeout 75
python scripts/run_release_tests.py --shard v57 --timeout 75
python scripts/run_release_tests.py --shard v571 --timeout 75
```

On a deployed sandbox:
```bash
MGC_BASE_URL=http://localhost:8080 python scripts/it_acceptance_v571.py --report docs/IT_ACCEPTANCE_REPORT_v5.7.1.md
python scripts/reliability_drill.py --base-url http://localhost:8080 --expect ready
python scripts/load_smoke.py --base-url http://localhost:8080 --requests 500 --workers 20 --username <user> --password <pass> --include-audio
python scripts/postgres_rls_check.py
bash scripts/backup_postgres.sh
bash scripts/restore_rehearsal.sh backups/<dump>
bash scripts/pitr_preflight.sh
```

## IT / content documents
- `docs/IT_ACCEPTANCE_v5.7.1.md`
- `docs/OBSERVABILITY_RECOVERY_v5.7.1.md`
- `docs/IT_ACCEPTANCE_v5.7.md`
- `docs/SECURITY_DATA_INTEGRITY_v5.7.md`
- `docs/CONTENT_GOVERNANCE_v5.7.md`
- `docs/ADAPTIVE_SRS_v5.7.md`
- `docs/OBSERVABILITY_v5.7.md`
- `docs/PITR_BACKUP_v5.7.md`
- `docs/IT_PILOT_RUNBOOK.md`
- `docs/IT_ACCEPTANCE_v5.5.md`
- `docs/PILOT_OPERATIONS_RUNBOOK_v5.5.md`
- `docs/DIALECT_COMPARISON_CONTENT_NOTE_v5.5.md`
- `docs/IT_ACCEPTANCE_v5.4.md` (previous release)
- `docs/RELIABILITY_RUNBOOK_v5.4.md`
- `docs/IT_ACCEPTANCE_v5.3.1.md` (previous release)
- `docs/IT_ACCEPTANCE_v5.3.md` (previous release)
- `docs/SECURITY_DECISIONS.md`
- `docs/PRONUNCIATION_TTS.md`
- `docs/CHINESE_LEARNING_DESIGN.md`
- `docs/PUTONGHUA_DIALECTS_CONTENT_NOTE.md`
- `CHANGELOG_v5.5.md`
- `CHANGELOG_v5.4.md` (previous release)
- `CHANGELOG_v5.3.1.md` (previous release)
- `CHANGELOG_v5.3.md` (previous release)

## Important language-content boundary
The app teaches **Putonghua first** because it is the practical nationwide standard for cross-regional communication. Regional varieties are presented as legitimate linguistic diversity, not as "incorrect Chinese". The overview says **10 major groups**, not "China has exactly 10 dialects".

## Important pronunciation boundary
The offline pilot voice prioritizes availability, privacy and deterministic deployment, not studio-quality native speech. It must not be used to demonstrate Cantonese/Wu/Min/etc. pronunciation: the included server voice is for standard Mandarin and English only. Dialect audio should be added later only from validated content/voice sources.

## Important production boundary
This package is a controlled pilot candidate, not unconditional production sign-off. Broad rollout still requires real corporate IdP testing, corporate TLS/ingress, secrets management, centralized rate limiting/WAF, SIEM retention, PostgreSQL HA/PITR according to IT standards, SCA/container policy and security review/pentest.

## v5.6 pilot governance and Chinese scope

- All core Chinese learning is **Putonghua (普通话)**. The UI repeats this on every main Chinese learning screen.
- `Информация о китайском` contains Pinyin, tones, Putonghua and regional/dialect orientation. Dialects are reference-only and never affect XP/course/exam/Skills Matrix.
- Admin can create pilot groups, rollout waves, members, feature overrides and learning-track assignments.
- Rollout waves support `draft / active / paused / completed`, planned start/end dates and editing from the Admin UI. Future waves do not activate before their start date.
- If an employee belongs to overlapping active groups, an explicit feature **deny wins** over an enable. This prevents accidental early rollout.
- Effective rollout state is available to each employee through `/api/pilot/me`; the home screen shows the employee's active pilot cohort/wave.
- Pilot results can be exported as UTF-8 CSV globally or by group, including separate English and Chinese Putonghua learning totals.
- Daily anti-abuse ceilings exist for XP, games, TTS and practice submissions; they are not learning goals. Duplicate practice retries do not consume quota twice.
- Pilot usage counters have configurable retention (`PILOT_USAGE_RETENTION_DAYS`, default 90) and participate in maintenance cleanup.
- v5.7 Alembic head: `c57d0a31f570`.

See `docs/PILOT_GOVERNANCE_RUNBOOK_v5.6.md`, `docs/PUTONGHUA_LEARNING_SCOPE_v5.6.md` and `docs/IT_ACCEPTANCE_v5.6.md`.


- Rollout Admin can edit wave status/dates, add/remove users, toggle feature flags, assign a topic/target/deadline and **Снять назначение** with audit logging.
- Release regression checks run in isolated shards with per-test timeouts.


## v5.7 security and data-integrity summary
- FastAPI RBAC + PostgreSQL RLS defense in depth for learning rows.
- 56 explicit authorization-matrix checks in addition to the existing security regression suite.
- Governed terminology lifecycle: draft/review → Admin approve/reject → published, with revision rollback and provenance.
- Tamper-evident audit chain with retention anchor.
- Adaptive SRS and due-review queue; XP remains an engagement economy, not a proficiency score.
- Question-quality analytics flag suspiciously difficult/easy items for content review without storing raw selected answers.
- Optional OpenTelemetry, Grafana dashboard and Prometheus rules.
- PITR preparation is included for rehearsal; real production RPO/RTO and off-host backup/WAL remain an IT/DBA acceptance requirement.


## v5.7.1 observability & recovery patch

- Alembic schema is unchanged: current head remains `c57d0a31f570`.
- SQLAlchemy query timing is collected in a bounded process-local window. Only normalized hash fingerprints, operation type and timings are retained; SQL text/parameters are not stored.
- Admin IT Dashboard shows DB query p95, slow-query count and PostgreSQL pool saturation.
- Prometheus exposes DB timing/pool metrics plus backup-age, restore-evidence-age and RPO/RTO target gauges.
- Pilot Compose includes a scheduled internal `backup` service (`pg_dump -Fc` + SHA-256 + retention).
- App reads `/backups` and `/wal_archive` read-only. Backup/WAL evidence never affects application readiness.
- `restore_rehearsal.sh` records measured restore duration in `*.restore-ok.json`; RTO status uses this measurement when available.
- `recovery_evidence_check.py` verifies backup/restore freshness without touching production data.
- `postgres_failure_drill.sh` is guarded by `CONFIRM_PILOT_DRILL=YES` and is intended only for an approved sandbox/pilot window.
- Same-host backups/WAL remain rehearsal-grade. Production DR still requires encrypted off-host durability and DBA evidence.
