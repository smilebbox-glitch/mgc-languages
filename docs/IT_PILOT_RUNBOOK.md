# MGC Languages v5.2 — IT Pilot Runbook

## Target topology
Corporate TLS/SSO reverse proxy (or pilot Nginx) → MGC Languages app → PostgreSQL.
Only the edge proxy publishes a host port. The application and database are isolated on an internal Docker network.

Pronunciation is generated locally in the app container with eSpeak NG. If that service is unavailable, the browser may use SpeechSynthesis as a graceful fallback.

## 1. Prepare configuration
```bash
cp .env.pilot.example .env.pilot
# Replace every CHANGE_ME value.
set -a; . ./.env.pilot; set +a
python scripts/pilot_preflight.py
```
For the first technical sandbox `AUTH_MODE=local` is supported. For a controlled corporate pilot use `AUTH_MODE=oidc`, disable self-registration, map corporate groups to User/Manager/Editor/Admin and configure `OIDC_DEPARTMENT_CLAIM`.

Optional OIDC configuration validation:
```bash
python scripts/oidc_config_check.py
# To fetch the discovery document as well:
OIDC_VERIFY_DISCOVERY=true python scripts/oidc_config_check.py
```

## 2. Build and start
```bash
docker compose --env-file .env.pilot -f docker-compose.pilot.yml build
docker compose --env-file .env.pilot -f docker-compose.pilot.yml up -d
docker compose --env-file .env.pilot -f docker-compose.pilot.yml ps
MGC_BASE_URL=http://localhost:8080 python scripts/container_smoke.py
python scripts/it_acceptance_v532.py
```
The app entrypoint runs `alembic upgrade head` before Uvicorn. `AUTO_CREATE_SCHEMA=false` in pilot.

## 3. Operational endpoints
- `/health/live` — process liveness.
- `/health/ready` — database/config readiness.
- `/api/pronunciation/status` — TTS mode/availability.
- `/metrics` — Prometheus-compatible pilot metrics; token protection is supported.
- `/api/admin/system/summary` — Admin configuration summary and findings.
- `/api/admin/pilot-telemetry` — adoption/learning/TTS/department telemetry.
- `/api/admin/audit` — privileged audit trail.

## 4. Department access boundary
`department` is stored on each user. In OIDC mode the value can be synchronized from the configured IdP claim. Managers can retrieve only users in their own department. Admin has global visibility. This is enforced in API authorization, not just hidden in UI.

## 5. Pronunciation acceptance
```bash
curl http://localhost:8080/api/pronunciation/status
curl -o /tmp/zh.wav 'http://localhost:8080/api/pronunciation/audio?language=chinese&text=%E8%B4%A8%E9%87%8F&rate=0.75'
file /tmp/zh.wav
```
Automated acceptance also checks the `RIFF` WAV signature. Audio is generated offline; no cloud TTS key is needed.

## 6. Backup and restore
```bash
set -a; . ./.env.pilot; set +a
bash scripts/backup_postgres.sh
bash scripts/restore_rehearsal.sh backups/<file>.dump
```
`restore_rehearsal.sh` creates a temporary database, restores the dump, checks migration/data tables and removes the test database. It does not overwrite the active pilot DB.

The older destructive restore remains available only for a deliberately approved recovery action:
```bash
CONFIRM_RESTORE=YES bash scripts/restore_postgres.sh backups/<file>.dump
```

## 7. Small load smoke
```bash
python scripts/load_smoke.py --base-url http://localhost:8080 --requests 500 --workers 20 --include-audio
```
This is an acceptance smoke, not production capacity certification.

## 8. Security controls in this build
- HttpOnly session cookie + CSRF token/header for state-changing cookie-auth requests.
- Configurable session TTL, registration, Secure/SameSite cookie policy.
- OIDC Authorization Code integration, group-to-role mapping and department claim mapping.
- Department-scoped Manager analytics.
- Trusted Host allowlist and optional explicit CORS allowlist.
- CSP, anti-clickjacking, no-sniff, referrer and permissions headers; HSTS with Secure cookies.
- In-memory pilot rate limiting on sensitive paths including TTS abuse control.
- Admin/editor terminology mutations, role and department changes are audited.
- Request IDs and structured JSON request logs.
- PostgreSQL connection pooling.
- Non-root read-only app container, capability drop, no-new-privileges.
- TTS is local/offline; no external voice API is required.

## 9. Controls left to corporate infrastructure
Before broad production: centralized rate limiting/WAF, SIEM shipping/retention, enterprise secrets manager, image/SCA policy, TLS lifecycle, PostgreSQL HA/PITR, formal performance test, real-IdP test evidence and penetration test.

## Migration concurrency
The app entrypoint runs `scripts/migrate_safe.py`. On PostgreSQL it takes a session advisory lock before `alembic upgrade head`; concurrent app starts wait up to `MIGRATION_LOCK_TIMEOUT_SECONDS`. Readiness additionally verifies the expected Alembic head before traffic is accepted.
