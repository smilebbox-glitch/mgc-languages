# CHANGELOG — MGC Languages v5.2

## Chinese learning UX
- Added `Chinese without fear` foundation block for absolute beginners.
- Explains Pinyin, 4 lexical tones + neutral tone, why tones matter and how context disambiguates real speech.
- Explains that Chinese has no alphabet equivalent to Russian; initials/finals are taught as a practical Pinyin sound map.
- Added simple tone gestures, real examples, common tone-change rules and automotive starter vocabulary.
- Added persistent user preference to show/hide Pinyin and approximate reading aids.

## Pronunciation
- Added local server-side WAV TTS endpoint for English and Chinese.
- Docker image installs eSpeak NG for offline pilot runtime.
- Browser SpeechSynthesis is automatic fallback rather than the only implementation.
- Added normal/slow audio buttons to vocabulary, examples, quizzes, roleplays and games.
- Added English IPA via CMU pronunciation data where available.
- Added approximate Russian reading hints for English and Pinyin; these are explicitly marked as learning aids, not phonetic truth.
- Added audio status endpoint, input length limit, simple abuse rate limit and LRU cache.

## Department RBAC / IT pilot
- Added user `department` field and Alembic migration.
- OIDC can sync department from configurable claim.
- Manager team analytics are restricted to the Manager's own department; Admin can view all departments.
- Added Admin department assignment endpoint for sandbox/pilot administration.
- Added pilot telemetry: active users, practice accuracy, game usage, language split, nudges, TTS state and department distribution.

## IT acceptance / operations
- Added v5.2 integration test verifying real RIFF/WAV output for Chinese and English.
- Added OIDC config checker.
- Added non-destructive HTTP load smoke.
- Added v5.2 post-deploy IT acceptance script.
- Added isolated restore rehearsal that restores a backup into a temporary PostgreSQL database and drops it afterward.
- Extended static preflight with Chinese-foundations validation, v5.2 tests and migration-to-head check.
