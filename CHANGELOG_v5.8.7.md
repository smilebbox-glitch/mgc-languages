# MGC Languages v5.8.7 — TTS Core Extraction

## Summary

v5.8.7 moves the stateful offline TTS engine out of the historical monolith and behind `mgc.tts_core`.

The v5.8.6 pronunciation router remains the HTTP boundary. v5.8.7 extracts synthesis, cache, health and circuit-breaker execution underneath it while preserving the existing API, browser fallback and Prometheus contracts.

## Extracted TTS core

New `mgc/tts_core.py` owns:

- semaphore/concurrency state;
- runtime success/failure/cache counters;
- health cache state;
- deterministic disk-cache path generation;
- disk cache read/write/TTL validation;
- disk-cache pruning;
- circuit breaker state and transitions;
- `@lru_cache(maxsize=256)` synthesis;
- offline `espeak-ng`/`espeak` subprocess execution;
- health probing for Chinese and English;
- pronunciation WAV response generation;
- safe browser-fallback behavior.

The core imports no legacy application module. Environment/config values and runtime hooks are injected explicitly.

## Compatibility bridge

New `mgc_core/tts_bridge.py` binds legacy TTS globals to the extracted core and fails closed on drift.

The bridge intentionally aliases the extracted mutable state back to:

- `_TTS_SEMAPHORE`
- `_TTS_RUNTIME_LOCK`
- `_TTS_RUNTIME`
- `_TTS_HEALTH_LOCK`
- `_TTS_HEALTH_CACHE`

This is required because the existing v5.8.1 observability boundary reads the TTS runtime counters directly. Pronunciation and Prometheus therefore use one shared state object rather than copied counters.

The bridge also rebinds:

- `_tts_cache_path`
- `_tts_cache_read`
- `_prune_tts_cache`
- `_tts_cache_write`
- `_tts_circuit_open`
- `_tts_mark_success`
- `_tts_mark_failure`
- `_synthesize_wav`
- `_tts_health`
- `_pronunciation_response`

## Runtime order

Relevant production order becomes:

`security -> governance -> learning -> services -> TTS core -> system/observability -> workflows -> auth core -> extracted routers -> route contracts`

TTS binds before observability so `/metrics` consumes the extracted runtime state.

## Preserved semantics

No change to:

- cache key prefix `v5.3.2`;
- SHA-256 cache filenames;
- RIFF and minimum-size cache validation;
- disk cache TTL;
- 80% prune target after exceeding configured max size;
- cache file permissions and atomic replace;
- LRU max size 256;
- circuit-breaker threshold and cooldown configuration;
- semaphore acquisition timeout;
- synthesis speed formula and bounds;
- Chinese/English voice selection;
- health-cache TTL;
- Chinese `你好` and English `hello` health probes;
- TTS runtime metric names/counters;
- rate limit `tts: 90/60s`;
- control-character cleanup;
- browser fallback/failure HTTP messages;
- operational telemetry event names;
- WAV response headers;
- feature flag and daily TTS quota handling in the pronunciation endpoint;
- API/OpenAPI paths;
- DB schema / Alembic head `c57d0a31f570`;
- runtime `APP_VERSION` fallback;
- UI and Putonghua content scope.

## Pronunciation boundary hardening

The v5.8.6 pronunciation router bridge now additionally requires the extracted TTS core and exposes `tts_core_bound` in its binding report.

## Tests

New `v587` release shard:

- `tests/v587_tts_core_test.py`
  - imports TTS core without the monolith;
  - validates deterministic cache key;
  - validates RIFF cache read/write and counters;
  - validates fake synthesis command and speed;
  - validates LRU=256 and disk-cache fallback;
  - validates circuit transitions;
  - validates bilingual health probing;
  - validates WAV response headers/rate limit;
  - validates disabled-engine browser fallback.

- `tests/v587_tts_runtime_test.py`
  - validates all production TTS globals are bound to `mgc.tts_core`;
  - validates state object identity;
  - validates pronunciation router requires the TTS core;
  - validates legacy pronunciation handlers resolve extracted TTS globals;
  - validates `/metrics` reads the same extracted TTS state;
  - validates authenticated safe fallback when TTS is disabled.

## CI

- `v587` added to the regression matrix;
- Docker gate validates `TTS_BINDING_REPORT` and pronunciation `tts_core_bound`;
- static preflight reports the TTS core boundary.

## Migration note

The historical TTS definitions remain physically present in `mgc/legacy_app.py` as fallback code during the staged migration. Production `asgi:app` executes the extracted TTS core through the runtime bridge.
