# Changelog v5.9.8

## Session & User Isolation Hardening

- added user-scoped storage for practice idempotency keys;
- preserved historical raw practice session compatibility for the same user;
- prevented cross-user collisions when two employees submit the same client `session_id`;
- extended workflow/router binding reports with `user_scoped_practice_sessions`;
- added multi-session/logout/expiry isolation regression coverage;
- added focused `v598` release shard and workflow;
- updated v579/v584 module-identity regressions for the isolation wrapper.

No API/OpenAPI, ORM schema, Alembic head, XP formulas, SRS, UI or language-content changes.
