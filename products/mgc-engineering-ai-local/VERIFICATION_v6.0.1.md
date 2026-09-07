# Verification — MGC Engineering AI Local v6.0.1

Verification performed against the final v6.0.1 source tree before release packaging.

## Backend regression

- Full backend suite: **236/236 PASS**.
- Dedicated v6.0.1 production-hardening / migration scenarios: **9/9 PASS**.
- v6.0 Engineering Intelligence OS and all previous v3.x–v5.8 domain regression remain included in the full suite.

## Security / authorization

- Human-facing API authorization: **190/190 guarded**.
- Explicit public/non-human exceptions: **4** (`/health`, `/health/live`, `/health/ready`, HMAC integration webhook).
- Dockerfile/Dockle-style static preflight: **32/32 PASS**.
- Compose/access/runtime security preflight: **84/84 PASS**.
- Worker-specific Celery healthcheck: PASS.
- API Docker healthcheck uses readiness rather than liveness: PASS.

## Operational hardening

- schema marker / migration idempotency: PASS;
- readiness fail-closed behavior: PASS;
- readiness output does not expose dependency URL/raw exception: PASS;
- optional dependency degradation policy: PASS;
- 503 on failed readiness: PASS;
- DR scripts/runbooks preflight: PASS;
- backup manifest + SHA-256 synthetic round-trip: PASS;
- restore requires explicit destructive-operation confirmation: PASS.

## Build / syntax

- Python compileall: PASS.
- Compose YAML parse: **12/12 PASS**.
- shell `bash -n`: PASS.
- TypeScript/TSX transpile syntax: **1/1 PASS**.
- CPU capacity preflight: PASS.
- `docker compose build` source/context preflight: PASS.
- `.env` is optional for build-stage Compose parsing by project configuration; production runtime secrets remain mandatory for acceptance.

## Runtime limitations of this environment

The following were **not executed** here because Docker CLI/daemon and Dockle are unavailable:

- real `docker compose build` image build;
- container runtime acceptance;
- Dockle image-layer scan;
- live PostgreSQL/Qdrant/storage backup and restore drill.

Run on the approved corporate build/runtime host:

```bash
docker compose build
make dockle
make acceptance
make backup
# Restore drill only in an approved isolated environment:
MGC_RESTORE_CONFIRM=RESTORE make restore BACKUP=/approved/path/to/backup
```

A restore drill must record measured RTO and evidence checks before production RPO/RTO is approved.
