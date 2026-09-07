# Adaptive SRS v5.7

The review engine is separate from XP. XP motivates; SRS schedules memory work.

Each card stores repetitions, lapses, ease factor, interval and next due date. Quality 0–2 resets the repetition chain; quality 3–5 expands intervals using an SM-2-inspired rule. Role/shop prioritization can be layered later without changing the storage model.

`GET /api/review/queue` returns due items. `POST /api/review/result` updates scheduling.

Question-attempt telemetry stores only a SHA-256 hash of the selected answer, not the raw selected text. Admin/Editor quality analytics flags questions with enough samples and unusually low/high accuracy. It is a content-quality signal, not an HR score.
