# MGC Languages v5.8.1 — Metrics & Observability Router

## Architecture

- Added `mgc.observability` as a dependency-light Prometheus text renderer.
- Added `mgc.routers.observability` as the active owner of `GET /metrics`.
- Added `mgc_core.observability_bridge` to inject existing runtime telemetry snapshots and replace the legacy metrics APIRoute in-place.
- Preserved the route position before the root `StaticFiles` mount.
- Historical `mgc.legacy_app` metrics endpoint is retained only as a compatibility/reference route object; production `asgi:app` executes the extracted router endpoint.

## Compatibility

- Prometheus metric names, HELP/TYPE lines, numerical formatting and order are preserved.
- `METRICS_ENABLED=false` still returns 404.
- Bearer-token protection still uses timing-safe comparison and returns 401 with `WWW-Authenticate: Bearer` on failure.
- No API path/method, database schema, Alembic, auth/session, XP/SRS, terminology, workflow, UI or language-content changes.
- Runtime `APP_VERSION` remains `5.7.1`; v5.8.1 is an engineering increment.

## Verification

- Dedicated `v581` core/runtime shard validates renderer output, token semantics, active route ownership and OpenAPI presence.
- Runtime test freezes variable telemetry snapshots and compares extracted vs historical Prometheus output byte-for-byte.
- Architecture guard now treats six routes as router-owned: five system routes plus `/metrics`.
- Docker CI validates both router binding reports before starting the application and running external smoke tests.
