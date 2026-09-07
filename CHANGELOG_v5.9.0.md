# MGC Languages v5.9.0 — Admin Operations Router Extraction

## Goal

Move the remaining operational/admin HTTP ownership out of the historical FastAPI monolith while preserving the existing observability, recovery, alerting and governance behavior.

## Extracted HTTP routes

`mgc.routers.admin_ops` owns 13 admin-only routes:

- `GET /api/admin/slo`
- `GET /api/admin/alerts`
- `PATCH /api/admin/alerts/{alert_id}/ack`
- `GET /api/admin/learning-error-telemetry`
- `GET /api/admin/pilot-telemetry`
- `GET /api/admin/analytics`
- `GET /api/admin/audit`
- `GET /api/admin/database/telemetry`
- `GET /api/admin/recovery/evidence`
- `GET /api/admin/it-dashboard`
- `POST /api/admin/maintenance/cleanup`
- `GET /api/admin/operational-events`
- `GET /api/admin/system/summary`

## Runtime boundary

`mgc_core.admin_ops_router_bridge` replaces the legacy APIRoutes fail-closed and verifies:

- exact 13-route contract;
- admin-only Auth Core binding;
- extracted User Service binding;
- Governance/Audit Core binding;
- shared extracted TTS Core health state;
- observability/recovery helper availability;
- `AlertAckPayload` schema parity;
- route name and response-class parity;
- StaticFiles ordering;
- endpoint ownership by `mgc.routers.admin_ops`.

The old handler implementations remain physically in `mgc/legacy_app.py` as migration fallback. Production `asgi:app` routes through the extracted router.

## Behavior preserved

No change to:

- SLO window calculations;
- recovery-state transitions;
- alert evaluation/acknowledgement semantics;
- database query/pool telemetry;
- recovery evidence and RPO/RTO reporting;
- maintenance cleanup and retention behavior;
- operational-event/audit persistence;
- IT dashboard payloads;
- learning-error and pilot telemetry;
- TTS health/circuit/cache telemetry;
- admin RBAC and CSRF rules.

## Verification

New `v590` shard covers:

- dependency-light exact route and payload contract;
- live ASGI endpoint ownership and mount order;
- non-admin `403`;
- SLO/alerts/learning/pilot/analytics/DB/recovery/IT endpoints;
- cleanup dry-run;
- operational events and system summary;
- alert acknowledgement and persisted audit event;
- OpenAPI path preservation.

## Compatibility

- no API URL change;
- no ORM/schema change;
- no Alembic migration; head remains `c57d0a31f570`;
- no runtime `APP_VERSION` bump;
- no frontend or language-content change;
- Putonghua remains the primary Chinese learning standard.

This is a stacked refactor over v5.8.9 and must not be merged to `main` until the preceding stacked PR chain and full GitHub Actions/Docker CI are green.
