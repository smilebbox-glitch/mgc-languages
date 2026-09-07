# MGC Languages v5.7.1 — Security / Data Integrity / Observability & Recovery

Unified English + Chinese corporate language-learning platform for automotive teams. v5.7.1 is a compatible patch on top of v5.7: it keeps RLS, governed terminology, audit chaining and adaptive SRS, then adds privacy-safe database timing telemetry, PostgreSQL pool saturation, measurable backup/restore evidence, pilot RPO/RTO visibility and an internal scheduled backup worker.

> GitHub baseline migration is in progress. Source learning data is restored and validated by CI before this repository is treated as the release source of truth.

## What a user gets
- English + Chinese under one account.
- Professional automotive vocabulary, tests, scenarios, SRS-style review, games and XP help economy.
- Chinese **«Информация о китайском»** module: Pinyin, tones, context, initials/finals, tone changes and starter technical words.
- **Tone Lab**: short ear training for the four main tones with immediate simple feedback.
- New **«Путунхуа и диалекты»** block:
  - what 普通话 means and why it is the practical standard for cross-regional work;
  - why Putonghua is not identical to everyday Beijing speech;
  - why there is no single exact count of local dialects;
  - the 10 major dialect groups used in the Ministry of Education overview;
  - simple examples: Sichuanese as Southwestern Mandarin, Cantonese as Yue, Shanghainese as Wu;
  - **side-by-side pronunciation comparisons** for `你好`, `吃饭` and `我不知道`: Putonghua versus selected Cantonese, Shanghai Wu, Chengdu/Sichuan, Hakka, Hokkien and Gan examples;
  - clear labels for Pinyin vs Jyutping vs regional romanization and a reminder that tone numbers are notation, not spoken digits;
  - accent vs local variety explained in plain language;
  - workplace phrase `请说普通话，可以吗？` with audio.
- Pinyin can be shown or hidden; approximate Russian reading can be hidden separately.
- Every term can be played at normal or slow speed.
- **No microphone, no voice recording, no pronunciation capture.** This release is playback-only.

## Pronunciation architecture
Primary pilot path:

`Browser → POST /api/pronunciation/audio → local eSpeak NG → WAV`

Fallback:

`Browser → SpeechSynthesis (zh-CN / en-US)`

v5.7 uses POST for pronunciation. In the pilot profile the legacy GET endpoint is disabled entirely, so normal learning text is not placed in pronunciation URLs/reverse-proxy access logs. Developer mode can still enable legacy GET explicitly for migration testing.
