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
- browser fallback if server TTS is unavailable.

## User-facing language scope
The application is explicit that the Chinese course teaches **Putonghua (普通话) — Standard Mandarin**. Dialect examples are reference-only and do not affect Chinese course progress, competency or XP.

## v5.7 security and data integrity
- PostgreSQL FORCE RLS policies for selected user-owned learning tables.
- Application RBAC remains in place as the first authorization layer.
- PostgreSQL session context is populated per authenticated request for RLS-aware deployments.
- PostgreSQL RLS checker verifies policy installation and rejects dangerous application DB roles with `rolsuper` or `rolbypassrls`.
- Content governance for custom terms: source traceability, revisions, review, Admin approval/rejection and rollback.
- Audit events are hash-chained and verifiable; retention preserves an anchor for the surviving chain.
- Adaptive SRS scheduling is separate from XP and tracks due date, repetitions, lapses, interval and ease factor.
- Question-quality telemetry aggregates attempts/accuracy/latency without retaining the raw selected answer; the answer is represented by a SHA-256 hash.

## v5.7.1 observability and recovery
- privacy-safe SQL timing instrumentation at the SQLAlchemy engine boundary;
- normalized statement fingerprints are SHA-256 hashed before storage/metrics — SQL text and parameters are not retained in application query telemetry;
- rolling DB p50/p95/p99, slow-query count and PostgreSQL pool saturation visibility;
- backup age and WAL evidence age;
- restore rehearsal evidence with measured restore duration;
- RPO/RTO targets surfaced to Admin/IT without turning stale recovery evidence into false application unavailability;
- Grafana dashboard + Prometheus alert rules for availability, HTTP 5xx, latency, DB latency/pool pressure and recovery evidence;
- optional OpenTelemetry FastAPI + SQLAlchemy tracing through OTLP/HTTP; observability is fail-open and must not become a service dependency.

## Roles
- **User** — personal learning, progress, games and own competency.
- **Manager** — department-scoped team analytics and assignments.
- **Editor** — governed terminology editing/review workflow.
- **Admin** — system administration, governance, security, audit, IT/recovery analytics.

## Pilot governance
The platform includes rollout waves, pilot groups, feature flags, training-track assignments and quota controls. A deny takes precedence when a user belongs to overlapping active groups with conflicting feature flags.

## XP and competence
XP is an engagement/reward mechanism, not a language-proficiency score. Competence remains a separate learning metric based on mastery, assessment accuracy and coverage. XP can be spent on optional help mechanics; it must not gate core learning content.

## Data and persistence
- PostgreSQL is the production persistence target.
- SQLite is retained for local development / deterministic MVP tests only.
- Alembic is the schema migration authority.
- v5.7.1 uses the same schema head as v5.7: `c57d0a31f570`.

## Production deployment
Required production controls include:
- `APP_ENV=production`;
- strong `SESSION_SECRET` and `BOOTSTRAP_ADMIN_PASSWORD` from a secret manager / deployment secret;
- HTTPS at the reverse proxy / ingress;
- `SESSION_HTTPS_ONLY=true`;
- corporate OIDC/SSO rather than local bootstrap auth for normal users;
- PostgreSQL, not SQLite;
- `AUTO_CREATE_SCHEMA=false`;
- Alembic migrations before application rollout;
- non-superuser PostgreSQL application role without `BYPASSRLS`;
- backup/WAL destinations outside the application host;
- central monitoring and audit/SIEM integration.

## Local quick start
Copy `.env.example` to `.env`, set a non-default admin password and then run:

```bash
docker compose up --build
```

For local-only development without Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export APP_ENV=development
export AUTO_CREATE_SCHEMA=true
export BOOTSTRAP_ADMIN_PASSWORD='choose-a-local-password'
uvicorn app:app --reload
```

Do not use the local profile as production configuration.

## Production compose
Use the production compose profile together with the deployment runbook and environment template. Exact command naming may be adapted by MGC IT to its internal container platform.

## Database migrations
Upgrade:

```bash
alembic upgrade head
```

Check current revision:

```bash
alembic current
```

Expected v5.7.1 head:

```text
c57d0a31f570
```

## Testing
Static/release preflight:

```bash
bash scripts/static_preflight.sh
```

Isolated regression shards:

```bash
python scripts/run_release_tests.py --shard base
python scripts/run_release_tests.py --shard pronunciation
python scripts/run_release_tests.py --shard putonghua
python scripts/run_release_tests.py --shard reliability
python scripts/run_release_tests.py --shard ops
python scripts/run_release_tests.py --shard v57
python scripts/run_release_tests.py --shard v571
```

Runtime acceptance:

```bash
python scripts/runtime_acceptance.py
```

PostgreSQL RLS acceptance on a real PostgreSQL deployment:

```bash
python scripts/postgres_rls_check.py
```

The PostgreSQL RLS check is intentionally separate: SQLite cannot prove PostgreSQL engine-level RLS behavior.

## Observability
Application metrics are available through the protected metrics endpoint. v5.7.1 also includes optional OpenTelemetry.

Example environment:

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=mgc-languages
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
DB_SLOW_QUERY_MS=250
DB_TELEMETRY_MAX_SAMPLES=512
RPO_TARGET_HOURS=24
RTO_TARGET_MINUTES=60
```

Reference assets:
- `deploy/otel/otel-collector-config.yaml`
- `deploy/grafana/mgc-languages-v571-dashboard.json`
- `deploy/prometheus/alerts-v571.yml`

## Backup and recovery
The package includes backup, restore rehearsal and PITR-preparation tooling. Recovery evidence is operational telemetry and does **not** gate readiness by default.

The production model is:

`PostgreSQL → backup/WAL → off-host encrypted storage → restore rehearsal → evidence → RPO/RTO dashboard`

The local pilot can demonstrate the mechanics, but MGC IT must validate real off-host storage, PostgreSQL WAL archiving and timestamp recovery on corporate infrastructure.

## Security boundary
The package provides application-level controls and deployment checks. It does not replace infrastructure security review, corporate IAM policy, vulnerability management, SIEM retention, database hardening or penetration testing.

## Release evidence
See:
- `RELEASE_VERIFICATION_v5.7.1.txt`
- `docs/IT_ACCEPTANCE_v5.7.1.md`
- `docs/RUNBOOK_v5.7.1.md`
- `CHANGELOG_v5.7.1.md`

Local release evidence for v5.7.1 includes 19 regression tests across isolated shards, a 56-case authorization matrix, 27 runtime acceptance checks and a 240-request concurrent smoke. These figures are release verification evidence, not a production SLA or capacity claim.
