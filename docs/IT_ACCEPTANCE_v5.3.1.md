# MGC Languages v5.3.1 — IT Pilot Acceptance

## Blocking checks
1. `GET /health/live` returns version `5.3.1`.
2. `GET /health/ready` returns `200` and `tts_legacy_get=disabled`.
3. PostgreSQL is used in the real pilot and Alembic is at head `c8f1a52e1a20`.
4. Pilot OpenAPI exposes **POST**, not GET, for `/api/pronunciation/audio`.
5. `Permissions-Policy` contains `microphone=()`.
6. `/api/meta` reports `voice_recording_enabled=false`, `pronunciation_transport=POST`, `legacy_tts_get_enabled=false` and `tts_cache_persistence=ephemeral`.
7. `/api/pronunciation/status` reports cache writability and both language checks.
8. If server TTS is healthy, Chinese and English synthesis return real RIFF/WAV bytes.
9. Manager analytics remain department-scoped; cross-department learning stats are denied.
10. Admin audit, pilot telemetry and system summary are accessible only to Admin.
11. Metrics require the configured bearer token when `METRICS_TOKEN` is set.
12. Self-registration is disabled for controlled pilot.

## Deployment commands
```bash
cp .env.pilot.example .env.pilot
# Replace all CHANGE_ME values.
set -a; . ./.env.pilot; set +a
python scripts/pilot_preflight.py
python scripts/oidc_config_check.py

docker compose --env-file .env.pilot -f docker-compose.pilot.yml build
docker compose --env-file .env.pilot -f docker-compose.pilot.yml up -d

MGC_BASE_URL=http://localhost:8080 python scripts/container_smoke.py
MGC_BASE_URL=http://localhost:8080 python scripts/it_acceptance_v531.py
```

## Recommended pilot smoke
```bash
python scripts/load_smoke.py \
  --base-url http://localhost:8080 \
  --requests 500 --workers 20 \
  --username <pilot-user> --password <password> --include-audio
```

## Still requires corporate infrastructure
- real OIDC discovery/login/logout and group/department claims;
- corporate TLS/DNS/ingress;
- secret manager rather than flat `.env` for production;
- PostgreSQL backup/isolated restore rehearsal;
- SIEM/log retention;
- SCA/container scanning and security review/pentest.
