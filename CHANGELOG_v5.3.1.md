# Changelog v5.3.1 — Putonghua / Privacy-first Pronunciation / Pilot Gate

## Learning content
- Keeps the beginner-first Putonghua module and 10-group overview from v5.3.
- Keeps the distinction between Putonghua, regional accents and local Chinese varieties.
- Keeps examples such as Sichuanese → Southwestern Mandarin, Cantonese → Yue and Shanghainese → Wu.
- No voice recording or microphone access was added.

## Pronunciation privacy
- Pilot profile is now **POST-only** for `/api/pronunciation/audio`.
- `TTS_LEGACY_GET_ENABLED=false` is the pilot default; the legacy GET route is not registered in the pilot API/OpenAPI surface.
- `/health/ready` fails in pilot/production if legacy GET is accidentally enabled.
- Server WAV responses explicitly use `Cache-Control: no-store`.
- Pilot TTS cache moved from a persistent named Docker volume to `/tmp` tmpfs.
- `TTS_CACHE_PERSISTENCE=ephemeral` is exposed in meta/system telemetry.
- Readiness verifies that the TTS cache is writable and that an ephemeral pilot cache is actually under `/tmp`.

## TTS resilience / observability
- Existing bounded concurrency, synthesis timeout, health TTL and circuit breaker remain.
- Added `cache_writable` and `cache_persistence` to pronunciation health.
- Added `mgc_tts_cache_writable` Prometheus gauge.
- Pilot telemetry exposes disk-cache enablement, writability, persistence and legacy GET state.
- Pilot tmpfs increased to 128 MB; TTS cache limit defaults to 64 MB with 24 h TTL.

## Pilot / IT
- Added `v531_privacy_readiness_test.py` negative/security contract.
- Added `it_acceptance_v531.py`.
- Static preflight now covers POST-only OpenAPI, ephemeral cache and readiness privacy gates.
- No database migration required. Alembic head remains `c8f1a52e1a20`.
