# MGC Languages v5.9.6 — Concurrent Write Integrity

## Fixed

- race-safe first creation of `PilotDailyUsage` under concurrent requests;
- race-safe first creation of `GamificationProfile`;
- lost-update risk for concurrent XP awards on the same user;
- lost-update risk for concurrent XP spending on the same user;
- daily quota increments now use a locked per-user/day row.

## Added

- `build_pilot_daily_usage_accessor()` in `mgc.services.learning`;
- Learning binding report fields `pilot_usage_bound` and `concurrent_write_safe`;
- `scripts/concurrent_write_load.py`;
- `tests/v596_learning_concurrency_test.py`;
- `tests/v596_concurrent_write_load_test.py`;
- release shard `v596`;
- focused PostgreSQL multi-worker concurrent-write CI gate;
- write-integrity documentation.

## Transaction model

- existing rows use `SELECT ... FOR UPDATE` on PostgreSQL;
- first-row creation is protected by `Session.begin_nested()` savepoints;
- unique-race losers re-fetch without rolling back the caller's outer transaction;
- different users remain independently parallel.

## Compatibility

- no API/OpenAPI change;
- no ORM/Alembic change; head remains `c57d0a31f570`;
- no runtime `APP_VERSION` bump;
- XP formulas/levels/reward pricing unchanged;
- UI/content unchanged;
- Путунхуа (普通话) scope unchanged.
