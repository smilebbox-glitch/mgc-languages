# Changelog v5.3 — Putonghua / Dialects / TTS Pilot Hardening

## Learning
- Added a beginner-first `普通话 / Putonghua` explainer.
- Added correct explanation that there is no single exact count of local dialects; UI presents the 10 major groups used in the Ministry of Education overview.
- Added 10 expandable group cards: Mandarin/Guanhua, Jin, Wu, Min, Hakka, Yue, Xiang, Gan, Hui, Pinghua/Tuhua.
- Added practical examples including Sichuanese → Southwestern Mandarin, Cantonese → Yue, Shanghainese → Wu.
- Added accent-vs-local-variety explanation and workplace guidance.
- Added `请说普通话，可以吗？` with standard Mandarin audio.
- Explicitly avoids dialect stereotyping and does not score employees on dialect knowledge.
- No voice recording was added.

## Pronunciation / TTS
- Frontend now uses `POST /api/pronunciation/audio` so text is not placed in new-client URLs.
- Legacy GET endpoint retained temporarily with deprecation headers.
- Added bounded TTS concurrency and configurable timeout.
- Added circuit breaker for repeated TTS engine failures.
- Replaced process-lifetime TTS health cache with TTL health state.
- Added optional bounded hashed disk WAV cache with retention.
- Added dedicated `ttscache` pilot volume.
- Added TTS success/failure/cache/circuit metrics.
- Browser SpeechSynthesis remains fallback.
- Dialect cards intentionally do not use fake dialect audio from a Mandarin voice.

## Security / pilot
- `Permissions-Policy` now explicitly denies microphone access.
- `/api/meta` and Admin system summary state that voice recording is disabled and pronunciation transport is POST.
- Added `X-MGC-Version: 5.3.0` response header.
- Updated load smoke to exercise POST audio.
- Static preflight now includes Tone Lab and v5.3 Putonghua/TTS/privacy tests.
- No database schema migration required; Alembic head remains `c8f1a52e1a20`.
