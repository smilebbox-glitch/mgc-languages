# v6.0.12 — Chinese Reference / Putonghua Foundations

- Added canonical `static/frontend/chinese_reference.js` ownership for `chinese-basics`.
- Preserved `chinese_reference` pilot feature gating and Chinese-only access.
- Moved Putonghua/Pinyin/tones/starter-word/reference rendering into the modular frontend.
- Moved Tone Lab 5-round practice into the module and preserved XP/practice submission through the existing practice contract.
- Kept dialect/regional examples reference-only; only Putonghua examples receive audio controls.
- Added explicit Putonghua learning-standard messaging so users know the main Chinese course, tests, XP and final exam are standard Chinese.
- Added navigation, boot, release-shard, preflight and dedicated CI coverage.
- Backend API/OpenAPI, ORM/Alembic, XP/SRS rules and language content data are unchanged.
- Historical `toneLabStart`, `renderToneLabRound` and `renderChineseBasics` remain in `static/app.js` as staged rollback fallbacks.
