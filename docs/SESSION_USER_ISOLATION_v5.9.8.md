# v5.9.8 — Session & User Isolation Hardening

## Goal

Make simultaneous office use safe across multiple employees and multiple browser sessions.

## Practice idempotency isolation

Historical `PracticeResult.session_id` is globally unique in the current schema. To avoid a migration during the pilot hardening sequence, new practice rows store a deterministic user-scoped key:

`u<user_id>:sha256(client_session_id)`

Consequences:

- two different users may submit the same client `session_id` without collision;
- duplicate detection remains idempotent for the same user;
- historical raw session IDs remain recognized for the same user;
- the public API and request payload remain unchanged;
- no Alembic migration is required.

## Session isolation

The regression contract verifies:

- two sessions for one user may coexist;
- logout deletes only the current `mgc_session` token;
- expiry of one token does not invalidate another user's session;
- gamification profiles remain user-specific;
- same client practice session IDs produce independent XP for different users.

## Verification

- `tests/v598_session_user_isolation_test.py`
- release shard `v598`
- focused workflow `.github/workflows/ci-v598.yml`
- v579 and v584 regressions continue to verify workflow scoring and router ownership.

## Compatibility

- API/OpenAPI unchanged;
- ORM schema unchanged;
- Alembic head remains `c57d0a31f570`;
- runtime `APP_VERSION` unchanged;
- XP formulas, SRS, games, terminology and language content unchanged;
- Путунхуа (普通话) remains the Chinese learning standard.
