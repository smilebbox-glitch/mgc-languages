# v5.9.4 — Capacity & Load Hardening

## Added

- fail-closed `scripts/capacity_preflight.py` for Uvicorn-worker / SQLAlchemy-pool / PostgreSQL connection budgeting;
- configurable `POSTGRES_MAX_CONNECTIONS`, DB reserve and auxiliary-connection budget in the LAN profile;
- bounded Uvicorn concurrency, backlog and keep-alive controls;
- PostgreSQL `max_connections` wiring in `docker-compose.lan.yml`;
- nginx upstream keep-alive reuse and tighter connect timeout;
- repeatable `smoke`, `office` and `burst` load profiles with success rate and p50/p95/p99 reporting;
- Windows launcher capacity migration/checks for existing `.env.lan` files;
- `v594` regression shard and focused PostgreSQL/app/nginx capacity gate;
- capacity sizing runbook.

## Compatibility

- no API/OpenAPI change;
- no ORM/Alembic change; head remains `c57d0a31f570`;
- no runtime APP_VERSION bump;
- no learning/XP/SRS/game/terminology behavior change;
- no frontend or language-content change;
- Putonghua (普通话) remains the primary Chinese learning standard.

## Capacity policy

v5.9.4 removes unsafe unbounded scaling assumptions but does not publish a fixed supported-user count. Final capacity must be measured on the target MGC server with real authenticated workload characteristics.
