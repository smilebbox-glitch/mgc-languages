# MGC Languages v5.8.6 — Pronunciation Router Extraction

## Summary

v5.8.6 moves pronunciation/TTS HTTP route ownership out of the historical FastAPI monolith and behind `mgc.routers.pronunciation`.

The existing offline synthesis implementation, cache, circuit breaker, pilot quota, feature flag and fallback behavior are intentionally preserved in this increment. The router delegates to the frozen handlers so HTTP ownership can move independently from the future TTS-core extraction.

## Extracted active routes

Always active:

- `GET /api/pronunciation/status`
- `POST /api/pronunciation/audio`

Conditionally active when `TTS_LEGACY_GET_ENABLED=true`:

- `GET /api/pronunciation/audio` (`deprecated=True`)

The compatibility GET remains disabled when the existing configuration disables it.

## Contract preservation

The router bridge fails closed unless all of the following remain true:

- `current_user` is the extracted `mgc.auth_core` dependency;
- the new `PronunciationPayload` schema is identical to the legacy payload schema;
- the environment-driven `TTS_MAX_CHARS` validation bound is unchanged;
- route names and response classes are preserved;
- the legacy GET deprecation flag is preserved when enabled;
- all replacement routes remain before the root StaticFiles mount;
- endpoint ownership is `mgc.routers.pronunciation`;
- router closures capture the original TTS handlers rather than reimplementing synthesis logic.

## Preserved behavior

No change to:

- offline `espeak-ng` / `espeak` synthesis selection;
- Chinese and English voice configuration;
- TTS health probing and cache TTL;
- disk cache and cache persistence modes;
- circuit-breaker thresholds/cooldown;
- rate limiting;
- `server_audio` feature flag;
- pilot daily TTS quota;
- POST transport that keeps training text out of URLs;
- browser fallback `503` behavior;
- legacy GET `Deprecation` / `Sunset` behavior after successful synthesis;
- API paths and methods;
- DB schema / Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI and Putonghua content scope.

## Tests

New release shard `v586`:

- `tests/v586_pronunciation_router_core_test.py`
  - imports/builds without `mgc.legacy_app`;
  - validates 2-route and 3-route configurations;
  - validates payload/rate/text limits;
  - validates legacy GET query alias and deprecation in OpenAPI.

- `tests/v586_pronunciation_router_runtime_test.py`
  - validates live ASGI ownership and binding report;
  - validates extracted auth dependency;
  - validates exact `TTS_MAX_CHARS` OpenAPI schema;
  - validates anonymous `401`;
  - validates safe `503` browser fallback with synthesis disabled;
  - validates POST and legacy GET validation behavior;
  - validates root StaticFiles ordering.

## CI

- `v586` added to the release regression matrix;
- Docker image gate validates `PRONUNCIATION_ROUTER_BINDING_REPORT`;
- static architecture guard now recognizes the pronunciation router ownership boundary.

## Next extraction

A later TTS-core increment can move synthesis, health/cache/circuit-breaker internals out of `mgc.legacy_app.py` without changing these HTTP routes again.
