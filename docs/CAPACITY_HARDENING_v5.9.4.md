# MGC Languages v5.9.4 — Capacity & Load Hardening

## Goal

Make the multi-user LAN deployment predictable under concurrent office use without claiming an unverified fixed user count.

The capacity chain is:

`browser -> nginx -> Uvicorn workers -> SQLAlchemy pools -> PostgreSQL`

Each Uvicorn worker is a separate process and therefore owns a separate SQLAlchemy connection pool. Increasing workers and DB pools independently can exhaust PostgreSQL even when CPU/RAM are still available.

## Default LAN topology

- Uvicorn workers: `2`
- per-worker DB pool: `5`
- per-worker max overflow: `5`
- theoretical application DB peak: `2 * (5 + 5) = 20`
- PostgreSQL `max_connections`: `120`
- reserved connections: `20`
- expected auxiliary connections: `8`
- usable application budget: `92`
- default headroom after theoretical application peak: `72`

These are conservative pilot defaults, not a production sizing recommendation for every server.

## Fail-closed connection budget

`scripts/capacity_preflight.py` runs before migrations and before Uvicorn starts.

It refuses startup when:

`WEB_CONCURRENCY * (DB_POOL_SIZE + DB_MAX_OVERFLOW) > POSTGRES_MAX_CONNECTIONS - DB_CONNECTION_RESERVE - CAPACITY_EXPECTED_AUX_CONNECTIONS`

This prevents a common scaling error where adding workers silently multiplies the number of possible DB connections.

## Admission control

The entrypoint now configures:

- `UVICORN_LIMIT_CONCURRENCY` — bounds concurrent requests accepted by a worker;
- `UVICORN_BACKLOG` — bounds socket backlog;
- `UVICORN_KEEP_ALIVE_SECONDS` — controls idle HTTP keep-alive lifetime;
- `DB_POOL_TIMEOUT` — bounds how long a request waits for a DB connection;
- `DB_POOL_RECYCLE` — periodically recycles long-lived DB connections.

The goal is bounded degradation rather than unbounded queues and database pressure.

## nginx

The edge proxy uses an upstream keep-alive pool so repeated browser requests do not create a new upstream TCP connection for every request. The application and database remain inaccessible directly from the LAN; only nginx publishes the LAN port.

## Repeatable load profiles

`scripts/multi_user_smoke.py` supports:

- `smoke`: 20 clients / 200 requests;
- `office`: 50 clients / 1000 requests;
- `burst`: 100 clients / 2000 requests.

Example:

```bash
python scripts/multi_user_smoke.py --base-url http://192.168.10.25:8080 --profile office
```

The report includes success rate, requests/sec, mean, p50, p95, p99 and maximum latency.

The probe mixes `/health`, `/health/live`, `/api/meta` and `/health/ready`; readiness exercises the database path. It is an infrastructure acceptance probe, not a full authenticated business-transaction benchmark.

## How to size on the real MGC server

1. Start with the default LAN topology.
2. Run the `smoke` profile.
3. Run `office` during an IT-approved test window.
4. Inspect CPU, RAM, PostgreSQL pool usage, DB p95 and HTTP p95.
5. Increase workers only if CPU/RAM have headroom and the connection budget remains safe.
6. Do not increase `DB_POOL_SIZE` and `WEB_CONCURRENCY` together without recalculating the total DB budget.
7. For larger rollout, use TLS/OIDC and run a workload containing authenticated learning/game/term requests, not only the infrastructure probe.

## Capacity claims

v5.9.4 deliberately does **not** claim that the service supports a fixed number such as 100, 500 or 1000 simultaneous employees. That number depends on server CPU/RAM, network, PostgreSQL storage latency, TTS usage and real user behavior. A supported concurrency figure should be recorded only after load testing on the target MGC infrastructure.
