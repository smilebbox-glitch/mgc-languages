# MGC Languages v5.9.5 — Authenticated Multi-User Load

## Goal

Validate concurrent office usage with real application sessions and authenticated API endpoints, not only `/health` and `/api/meta`.

This is a capacity verification tool. It does **not** declare a fixed supported-user count for production. Final sizing must be repeated on the target MGC server, network and PostgreSQL instance.

## What the workload exercises

Each request carries a normal `mgc_session` cookie and passes through the same `current_user`, DB session and RLS-aware application path used by the browser UI.

The mixed read workload includes:

- `GET /api/me`
- `GET /api/gamification/me`
- `GET /api/learning/preferences`
- `GET /api/review/queue?language=chinese&limit=10`
- `GET /api/language/chinese/summary`
- `GET /api/language/english/quiz?count=5`

This deliberately combines session lookup, user data, gamification, SRS/review and language-content work.

## Test-only session fixtures

`scripts/seed_authenticated_load.py` creates isolated users and short-lived sessions directly in the test database. It is intentionally not an HTTP endpoint and is fail-closed:

- requires `LOAD_TEST_FIXTURES_ENABLED=true`;
- refuses to run when `APP_ENV=production`;
- stores only SHA-256 session-token digests in PostgreSQL, matching normal session storage;
- raw tokens exist only in the temporary local sessions file used by the load client.

Do not use this fixture utility against production data.

## Profiles

`scripts/authenticated_load.py` provides three starting profiles:

| Profile | Authenticated users | Requests | Default success threshold | Default p95 threshold |
|---|---:|---:|---:|---:|
| pilot | 20 | 400 | 100% | 3000 ms |
| team | 50 | 1000 | 99.5% | 3000 ms |
| burst | 100 | 2000 | 99.0% | 4000 ms |

These are test profiles, not capacity claims.

## Sanitized report

Use `--report-file` to persist a JSON report. The report contains aggregate counts, request rate and latency percentiles only. It never includes usernames, session tokens or cookie values.

Example:

```bash
python scripts/authenticated_load.py \
  --base-url http://127.0.0.1:8080 \
  --sessions-file /tmp/mgc-auth-sessions.json \
  --profile team \
  --report-file /tmp/mgc-auth-load-report.json
```

## Focused CI acceptance

`.github/workflows/ci-v595.yml` performs:

1. v5.9.5 tool-contract test;
2. PostgreSQL + modular ASGI + nginx LAN startup;
3. readiness check;
4. seeding 50 isolated short-lived sessions;
5. 1000 authenticated mixed API requests through nginx;
6. sanitized-report validation;
7. PostgreSQL connection-pressure check;
8. modular ASGI contract check;
9. ephemeral database teardown.

The sessions file is deleted and is never uploaded as an artifact. Only the sanitized aggregate report may be retained for seven days.

## Interpreting results

A successful run proves that this deployment/configuration handled that specific workload under those test conditions. It does not prove that the same user count is safe on a different server or with a different workload mix.

For MGC rollout, repeat tests on the real server while observing CPU, memory, PostgreSQL pool saturation, p95/p99 latency and error rate. Increase concurrency gradually and keep the v5.9.4 DB connection budget valid.

## Chinese learning scope

The load test does not modify course content. Chinese learning remains explicitly based on **Путунхуа (普通话)**; dialect material remains reference-only.
