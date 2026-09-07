# MGC Languages v5.3.2 — IT Pilot Acceptance

## Automated release gate
Run:

```bash
bash scripts/static_preflight.sh
```

Expected result: `PASS: v5.3.2 static pilot preflight`.

## Configuration preflight
Load the reviewed pilot env and run:

```bash
set -a; . ./.env.pilot; set +a
python scripts/pilot_preflight.py
```

Blocking conditions include placeholder secrets, wildcard Trusted Hosts/CORS, legacy GET pronunciation, invalid cookie policy and policy-gate contradictions.

## Deployment acceptance
After `docker compose ... up -d`:

```bash
MGC_BASE_URL=https://<pilot-host> \
METRICS_TOKEN="$METRICS_TOKEN" \
MGC_ADMIN_USERNAME="$MGC_ADMIN_USERNAME" \
MGC_ADMIN_PASSWORD="$MGC_ADMIN_PASSWORD" \
AUTH_MODE="$AUTH_MODE" \
python scripts/it_acceptance_v532.py
```

Acceptance checks:
1. `/health/live` returns version `5.3.2`.
2. `/health/ready` reports ready.
3. `checks.schema_head.status == ok` and current head is `c8f1a52e1a20`.
4. Pilot policy reports explicit Trusted Hosts/CORS and disabled legacy pronunciation GET.
5. When enabled by policy, self-registration is disabled, metrics are bearer-protected, OIDC is active and cookies are Secure.
6. Putonghua foundations contain 10 major dialect-group overview cards and workplace guidance.
7. No voice-recording capability is exposed.
8. Pronunciation uses POST and returns a real RIFF/WAV stream when server TTS is available.
9. Admin telemetry/system summary are accessible only with Admin privileges.
10. `/metrics` requires the configured bearer token.

## Schema-drift behavior
The application intentionally returns HTTP 503 from readiness if the DB is reachable but the Alembic head is stale or missing while `READY_REQUIRE_SCHEMA_HEAD=true`. This prevents a rolling deployment from advertising an incompatible instance as ready.

## Corporate pilot profile
Recommended after corporate ingress/IdP integration:

```env
AUTH_MODE=oidc
READY_REQUIRE_OIDC=true
REGISTRATION_ENABLED=false
READY_REQUIRE_REGISTRATION_DISABLED=true
COOKIE_SECURE=true
READY_REQUIRE_SECURE_COOKIE=true
READY_REQUIRE_SCHEMA_HEAD=true
READY_REQUIRE_METRICS_TOKEN=true
TTS_LEGACY_GET_ENABLED=false
TTS_CACHE_PERSISTENCE=ephemeral
```

## Target-environment checks still required
- Real corporate PostgreSQL backup + isolated restore rehearsal.
- Corporate OIDC login/logout, claims, role groups and department mapping.
- Corporate TLS/DNS/ingress and Secure-cookie validation.
- SIEM/log collector ingestion and retention.
- SCA/container scan and security review/pentest according to IT policy.
- Capacity/load testing on the actual pilot host; the included load smoke is only a functional concurrency gate.
