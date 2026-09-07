# MGC Languages v5.7.9 — Practice & Game Workflow Service

## Scope

v5.7.9 extracts high-level learning orchestration from the legacy monolith at the ASGI runtime boundary while preserving the registered FastAPI API contract.

### Extracted workflows

- `POST /api/practice/result`
- `POST /api/learning/question-attempt`
- `POST /api/games/{game_type}/start`
- `POST /api/games/{session_id}/finish`

The extracted `mgc.services.practice_games` layer owns practice XP scoring, duplicate handling, question-attempt SRS updates, game construction, answer scoring and game XP completion logic.

## Runtime order

`security -> governance -> learning -> user/terminology services -> practice/game workflows -> auth -> route contracts`

This order is deliberate. Practice/game workflows capture the already-extracted learning and terminology services rather than legacy helpers.

## Compatibility

Unchanged:

- public API paths, methods, request payloads and response shapes;
- FastAPI body/query/dependency metadata and OpenAPI contract;
- database schema and Alembic head `c57d0a31f570`;
- practice XP formulas;
- XP idempotency and anti-farm behavior;
- daily practice/game quotas;
- game types: `match`, `listening`, `mistake`, `phrase`;
- game scoring and completion XP formula;
- SRS updates for question attempts;
- UI and language content;
- Chinese learning standard: Путунхуа (普通话).

## Safety gates

`mgc_core.workflow_bridge` fails closed when:

- any of the four target routes is missing or duplicated;
- route method/path contracts drift;
- required ORM columns drift;
- workflow binding happens before extracted Learning Service;
- workflow binding happens before extracted Terminology Service.

Dedicated `v579` tests cover pure scoring behavior and the live ASGI practice/question/game lifecycle.
