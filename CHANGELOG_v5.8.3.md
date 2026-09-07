# v5.8.3 — Learning Router Extraction

## Goal

Move active progress, 30-day course, SRS review, gamification and learning-preference HTTP ownership out of the historical FastAPI monolith while preserving the already-extracted auth, XP/SRS and terminology service contracts.

## Extracted router

`mgc/routers/learning.py` now owns 12 active routes:

- `GET /api/language/{language}/progress`
- `POST /api/language/{language}/progress`
- `GET /api/language/{language}/course30`
- `POST /api/course-day/result`
- `GET /api/review/queue`
- `POST /api/review/result`
- `GET /api/gamification/me`
- `GET /api/gamification/levels`
- `GET /api/gamification/rewards`
- `POST /api/gamification/spend`
- `GET /api/learning/preferences`
- `PUT /api/learning/preferences`

The router exposes explicit FastAPI signatures and delegates the remaining thin orchestration bodies to frozen legacy handlers. Those handlers already resolve `gamification_view`, `level_info`, `spend_xp`, `get_or_create_srs_card`, `schedule_srs`, `terms_for` and `term_by_id` through the extracted service bindings established in v5.7.7-v5.7.8.

## Runtime binding

`mgc_core/learning_router_bridge.py`:

- validates the exact 12-route contract;
- requires auth core, XP/SRS core and terminology service bindings before activation;
- replaces legacy APIRoutes in-place, preserving route order before the root StaticFiles mount;
- preserves route names and response classes;
- fails closed on missing/duplicate/drifted routes or service bindings;
- rebinds legacy module route names to the active router endpoints for compatibility.

Runtime order remains deliberately staged:

`security -> governance -> learning core -> user/terminology services -> system/observability/workflows -> auth core -> auth router -> learning router -> API contract validation`

## Compatibility

No changes to:

- API paths/methods or frontend calls;
- XP level curve, reward catalog or spendable/lifetime XP behavior;
- anti-farm/idempotency/daily XP policy;
- SRS scheduling semantics;
- course completion thresholds;
- progress statuses (`learning` / `known`);
- learning preference fields;
- schema or Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback (`5.7.1`);
- auth/session/security/RLS/audit;
- English/Chinese content or Putonghua learning standard.

## Verification

New `v583` regression shard verifies:

- dependency-light router construction without importing `mgc.legacy_app`;
- exact 12-route contract and payload validation;
- runtime route ownership and root mount ordering;
- captured extracted auth/XP-SRS/terminology bindings;
- live gamification/profile/levels/rewards;
- learning preferences read/write;
- 30-day course and progress update;
- SRS queue/review result;
- course-day failure semantics;
- XP earn via practice workflow and spend through the new router;
- OpenAPI path continuity.

All previous regression shards and Docker runtime smoke remain required before merge.
