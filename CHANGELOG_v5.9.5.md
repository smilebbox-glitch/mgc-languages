# MGC Languages v5.9.5 — Authenticated Multi-User Load

## Added

- `scripts/seed_authenticated_load.py` for explicit test-only user/session fixture creation;
- `scripts/authenticated_load.py` mixed authenticated workload probe;
- pilot/team/burst profiles;
- aggregate success rate, requests/sec, mean, p50, p95, p99 and max latency reporting;
- optional sanitized JSON report file with no tokens or usernames;
- `tests/v595_authenticated_load_test.py`;
- release shard `v595`;
- focused PostgreSQL + ASGI + nginx authenticated-load CI workflow;
- documentation for interpreting capacity results.

## Safety

- fixture seeding requires `LOAD_TEST_FIXTURES_ENABLED=true`;
- fixture seeding is blocked in `APP_ENV=production`;
- session tokens are stored in PostgreSQL only as digests;
- raw fixture tokens are temporary CI input and are never uploaded as artifacts;
- load report contains aggregate metrics only.

## Compatibility

- no API/OpenAPI change;
- no ORM/Alembic change; head remains `c57d0a31f570`;
- no runtime `APP_VERSION` bump;
- no learning/XP/SRS/games/terminology/UI/content change;
- Путунхуа (普通话) remains the Chinese learning standard.

## Capacity statement

v5.9.5 adds authenticated workload evidence, not a fixed production user-count claim. Final sizing remains dependent on the target MGC server and real workload.
