# MGC Languages v5.9.6 — Concurrent Write Integrity

## Problem addressed

Multi-worker deployment changes the failure mode from simple throughput pressure to database concurrency. Several requests for the same user may arrive at different Uvicorn workers at the same time.

The historical first-use pattern for `PilotDailyUsage` and `GamificationProfile` was:

`SELECT row → if missing INSERT row`

Under concurrent first writes this can race on unique constraints. In addition, ordinary read-modify-write XP increments can lose updates when two transactions read the same profile value before either commits.

## Hardening

v5.9.6 keeps the existing API and XP semantics but changes the transactional mechanics for write paths:

- `PilotDailyUsage` accessor selects an existing per-user/day row with `FOR UPDATE`;
- first-row creation uses a nested transaction/savepoint;
- if another transaction wins the unique insert race, the losing request rolls back only the savepoint and re-fetches the row;
- XP award mutations lock the user's `GamificationProfile` with `FOR UPDATE`;
- XP spending uses the same profile lock;
- requests for different users remain independent and can proceed concurrently.

This preserves the outer FastAPI request transaction and avoids a full rollback when the race happens.

## Why the lock order matters

Practice-result writes acquire the daily-usage row first and the gamification profile second. Concurrent award paths follow the same order. Consistent lock order reduces deadlock risk while serializing only the rows owned by one user.

## Verification workload

`scripts/concurrent_write_load.py` uses real `mgc_session` authentication and CSRF cookie/header pairing. The focused gate uses:

- 50 authenticated users;
- 5 concurrent perfect quiz writes per user;
- 250 unique `PracticeResult` rows total;
- 250 XP events;
- exact 200 XP delta per user;
- exact daily usage counters per user;
- one duplicate replay per user, which must not add XP.

The test validates PostgreSQL rows after the HTTP workload and checks the runtime binding report for the race-safe accessor.

## Report safety

The write report contains aggregate counts, generated practice session IDs and numeric user IDs used by the isolated test database. It does not contain raw authentication session tokens, cookies or passwords. The raw load-session fixture file is temporary and is never uploaded as an artifact.

## Compatibility

- no endpoint or OpenAPI change;
- no ORM table or Alembic migration change;
- XP award formulas and level thresholds are unchanged;
- SRS/content/UI are unchanged;
- runtime `APP_VERSION` is unchanged;
- Chinese learning remains based on **Путунхуа (普通话)**.
