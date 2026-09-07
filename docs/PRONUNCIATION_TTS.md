# Pronunciation / TTS design — v5.2.2

## Problem
Browser-only `speechSynthesis` is not deterministic: voice inventory depends on OS/browser policy. A visible listen button can therefore exist while the desired English or Mandarin voice does not.

## Pilot design
Primary path:

`GET /api/pronunciation/audio?language=chinese|english&text=...&rate=...`

The application invokes a local TTS binary and returns real `audio/wav`. The pilot Docker image installs eSpeak NG. No cloud TTS connection or runtime Internet is required.

Fallback path:

`SpeechSynthesisUtterance` with `zh-CN` or `en-US`.

The frontend gives the server request a six-second timeout. A network/TTS failure therefore degrades to browser speech instead of leaving a dead control.

## Reliability controls
- `/api/pronunciation/status` performs an actual short synthesis probe for both languages.
- Per-language health is returned in `language_checks`.
- WAV signature is verified server-side and in integration tests.
- Maximum input length and TTS-specific rate limiting.
- In-process LRU cache for repeated phrases.
- Audio responses remain `no-store`; repeated synthesis is optimized only by the application in-memory cache.
- Engine and configured voice are exposed in response headers for IT diagnosis.
- Normal and slow playback controls.
- Audio button busy state prevents repeated accidental clicks.
- Readiness reports degraded pronunciation without taking the core learning service down.
- Pilot Admin telemetry exposes TTS health and cache hits/misses.

## Chinese sound-map correctness
Do not send isolated Latin `q`, `x`, `zh` etc. to TTS as a pronunciation example: an engine may read a letter name. The beginner sound map therefore binds each Pinyin initial/final to a real Chinese character/syllable and plays that Hanzi.

Examples:
- `q` → 气 `qì`
- `x` → 小 `xiǎo`
- `zh` → 中 `zhōng`
- `ch` → 车 `chē`

## English pronunciation metadata
Known words use CMU pronunciation data to generate IPA and a temporary Russian reading aid. Unknown all-uppercase technical acronyms up to eight letters are spelled as English letter names, e.g. `PPAP → пи-пи-эй-пи`.

## Quality boundary
Offline eSpeak NG prioritizes availability/privacy over voice naturalness. For broad production the `/api/pronunciation/audio` contract can be backed by an approved enterprise or neural TTS engine. The frontend does not need to change.

## v5.3 transport/privacy and resilience update
New clients use:

`POST /api/pronunciation/audio`

with `{language, text, rate}` in the JSON body. This avoids putting the learning phrase into the request URL and common reverse-proxy access logs. The previous GET contract is temporarily retained only for backwards compatibility and sends `Deprecation: true`.

Additional pilot controls:
- bounded synthesis concurrency (`TTS_CONCURRENCY`);
- configurable subprocess timeout;
- circuit breaker after repeated failures with bounded cooldown;
- health state uses a short TTL rather than a process-lifetime cached result;
- optional hashed WAV disk cache with max-size and TTL limits;
- dedicated writable `ttscache` volume while the application filesystem remains read-only;
- TTS success/failure/cache/circuit Prometheus metrics;
- filenames in the TTS cache are SHA-256 hashes, not phrase text.

The API middleware keeps audio API responses `no-store` at the HTTP layer. The server-side cache is an internal availability optimization.

## Dialect-audio boundary
The standard Mandarin TTS voice must **not** be presented as Cantonese, Wu, Min, Hakka or another regional variety. v5.3 provides informational dialect cards only. Dialect audio requires separately validated voices/content.

## Microphone boundary
No microphone API is used and no speech is recorded. The service is playback-only in this release.
