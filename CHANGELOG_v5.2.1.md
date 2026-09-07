# CHANGELOG — MGC Languages v5.2.1

## Chinese beginner experience
- Completed the Pinyin sound map with `g/k/h` and the difficult `j/q/x`, `zh/ch/sh/r`, `z/c/s` groups.
- Every initial and final now has a real Hanzi example, Pinyin, approximate Russian reading and an audio button. The audio plays the Chinese syllable, not the Latin letter name.
- Added a four-step beginner path: hear → repeat → hide Cyrillic reading → gradually hide Pinyin.
- Added explicit guidance that Cyrillic readings are temporary scaffolding and audio is the pronunciation reference.
- Added practical pronunciation targets for Russian speakers rather than demanding a perfect accent.

## Pronunciation reliability
- TTS status now performs real Chinese and English synthesis probes instead of treating binary presence as success.
- Added per-language TTS health in `/api/pronunciation/status`.
- Server audio responses include engine/voice headers and `no-store` audio responses while keeping an in-process synthesis cache.
- Frontend server-audio request has a six-second abort timeout and automatically falls back to browser SpeechSynthesis.
- Audio buttons display a busy state while loading.
- Fixed duplicated pronunciation text in vocabulary cards.
- Pilot telemetry now includes TTS language checks and in-process audio-cache statistics.

## English technical reading aids
- Added readable spelling for unknown all-uppercase technical acronyms such as `PPAP` and `CMM`.
- Existing CMU-based IPA and approximate Cyrillic reading remain the preferred path for known English words.

## QA / acceptance
- Added `v521_pronunciation_quality_test.py` covering Pinyin reading aids, complete sound-map examples, acronym pronunciation, real TTS health, WAV headers/cache and frontend timeout fallback.
- No schema migration is required from v5.2; Alembic head remains unchanged.
