# v5.8.4 — Practice & Games Router Extraction

## Summary

v5.8.4 moves the four active practice/game HTTP routes out of legacy route ownership and into a dedicated FastAPI `APIRouter` while preserving the v5.7.9 workflow service as the business-logic owner.

### Active route ownership moved

- `POST /api/practice/result`
- `POST /api/games/{game_type}/start`
- `POST /api/games/{session_id}/finish`
- `POST /api/learning/question-attempt`

The new HTTP owner is `mgc.routers.practice_games`.

## Runtime architecture

The v5.7.9 `mgc.services.practice_games` workflow layer remains responsible for:

- practice XP calculation;
- duplicate/idempotency protection;
- daily quota enforcement;
- question-attempt persistence;
- SRS updates from question attempts;
- game pool/session generation;
- answer scoring;
- game completion and perfect-game bonus;
- duplicate game-finish protection.

`mgc_core.practice_games_router_bridge` replaces the four workflow-bound legacy `APIRoute` objects in-place with routes built by `mgc.routers.practice_games`.

The bridge fails closed unless:

- all four routes exist exactly once;
- route names and response classes are preserved;
- all routes stay ahead of the root StaticFiles mount;
- route endpoints are owned by `mgc.routers.practice_games`;
- `current_user` is the extracted `mgc.auth_core` implementation;
- all workflow handlers are owned by `mgc.services.practice_games`;
- v5.7.9 workflow bindings still confirm extracted learning and terminology services.

## Runtime order

Relevant production ordering is now:

`security -> governance -> learning -> services -> workflow service -> auth core -> auth router -> learning router -> practice/games router -> route contracts`

## Compatibility

No intentional changes to:

- API paths or HTTP methods;
- request payload validation;
- CSRF/auth requirements;
- OpenAPI paths;
- XP economy or level curve;
- anti-farm/idempotency rules;
- SRS scheduling;
- game scoring or bonuses;
- database schema;
- Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI or language content;
- Chinese learning standard: Путунхуа (普通话).

Legacy route definitions remain physically present in `mgc/legacy_app.py` as fallback/reference code, but deployed `asgi:app` owns these four routes through `mgc.routers.practice_games`.

## Verification

New `v584` regression shard verifies:

- dependency-light independent router import;
- exact four-route contract;
- payload validation parity;
- live route ownership and root mount ordering;
- extracted auth/workflow binding capture;
- perfect quiz XP = 40;
- duplicate practice protection;
- question-attempt duplicate protection and SRS update;
- match-game lifecycle and perfect completion bonus;
- duplicate finish protection;
- OpenAPI path presence.

CI and Docker gates additionally require the practice/games router binding report to be healthy inside the built image.
