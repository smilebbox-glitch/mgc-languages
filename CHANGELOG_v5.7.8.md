# MGC Languages v5.7.8 — Learning & Gamification Service

## Goal

Continue decomposition of `app.py` by moving the reusable learning mechanics that carry state and business rules into a modular service while preserving all public routes, persistence schema and learning content.

## Extracted production mechanics

`mgc.services.learning` now owns the production implementations for:

- weekly XP profile rollover;
- 100-level progression metadata;
- gamification profile projection;
- XP awards and idempotency;
- anti-farming multipliers (100% → 50% → 10%);
- daily XP-cap enforcement;
- spendable-XP purchases without reducing lifetime XP;
- SRS card creation;
- SM2-inspired interval/ease scheduling.

`mgc_core.learning_bridge` validates the legacy ORM/reward contracts and rebinds the corresponding module globals before downstream services are built.

## Runtime order

The stable ASGI boundary now binds:

`security -> governance/RLS -> learning -> user/terminology services -> auth -> API contracts`

The order is intentional. `user_admin_stats` from v5.7.7 captures `gamification_view` during service construction, so learning must be bound first to ensure Admin/Manager statistics use the extracted XP implementation.

## Compatibility

Unchanged:

- all API paths/methods and FastAPI route objects;
- `GamificationProfile`, `XPEvent`, `SRSCard` tables and Alembic head `c57d0a31f570`;
- 500 XP per level and the 100-level title progression;
- lifetime vs spendable XP semantics;
- reward prices/catalog;
- duplicate/idempotency behavior;
- 24-hour anti-farming thresholds;
- pilot daily XP cap;
- SM2-inspired SRS intervals/ease-factor behavior;
- UI, English/Chinese content and Путунхуа (普通话) learning standard.

No database migration is required.

## Verification

The `v578` CI shard verifies both an isolated learning service and live `asgi:app` execution, including perfect-quiz XP, duplicate practice handling, XP spending, repeated SRS scheduling, 100 levels, and Admin statistics consuming the extracted gamification view. Docker CI additionally asserts the learning binding before starting the container and running the existing external runtime smoke test.
