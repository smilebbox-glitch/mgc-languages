# MGC Languages v5.4 — IT Pilot Acceptance

## 1. Static release gate
```bash
bash scripts/static_preflight.sh
```
Expected: `PASS: v5.4 static pilot preflight`.

## 2. Clean database
```bash
AUTO_CREATE_SCHEMA=false DATABASE_URL=<pilot-db-url> alembic upgrade head
alembic current
```
Expected Alembic head: `f54c0a91b723`.

## 3. Runtime acceptance
```bash
MGC_BASE_URL=http://localhost:8080 python scripts/it_acceptance_v54.py
```
For local-auth sandbox, export `MGC_ADMIN_USERNAME`, `MGC_ADMIN_PASSWORD` and `METRICS_TOKEN` first.

Acceptance checks include:
- liveness and readiness;
- exact schema head;
- DB latency readiness signal;
- `Информация о китайском` content and 10-group Putonghua overview;
- no voice recording;
- IT dashboard;
- maintenance dry-run;
- operational Prometheus metrics;
- real WAV pronunciation when offline TTS is healthy.

## 4. Reliability drill — PostgreSQL outage
Only on a dedicated pilot/sandbox window:
```bash
python scripts/reliability_drill.py --base-url http://localhost:8080 --expect ready

docker compose --env-file .env.pilot -f docker-compose.pilot.yml stop db
python scripts/reliability_drill.py --base-url http://localhost:8080 --expect db-down

docker compose --env-file .env.pilot -f docker-compose.pilot.yml start db
# wait for DB and app readiness
python scripts/reliability_drill.py --base-url http://localhost:8080 --expect ready
```
Expected during DB outage:
- `/health/live` = 200;
- `/health/ready` = 503;
- app instance is not considered ready for traffic;
- authenticated DB-backed API returns controlled retryable 503 rather than a stack trace.

## 5. TTS degradation
If offline TTS is deliberately disabled in a sandbox/restarted app:
- core learning remains available;
- `/api/pronunciation/status` reports server audio unavailable;
- pronunciation buttons use browser SpeechSynthesis fallback;
- TTS failure does not make `/health/ready` fail solely because browser fallback is an intentional supported mode.

## 6. Maintenance / retention
Admin UI → `IT · состояние пилота` → `Проверить cleanup` should be reviewed first.
Automated pilot maintenance runs in an internal container with no host port.
Final retention values require IT/Security/HR approval before production.

## 7. Backup / restore
```bash
bash scripts/backup_postgres.sh
bash scripts/restore_rehearsal.sh backups/<dump>
```
A restore rehearsal is required before expanding the pilot.
