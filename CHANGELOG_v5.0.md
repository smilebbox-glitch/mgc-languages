# MGC Languages v5.0 — Gamification Pilot

## Added
- 100 equal XP levels: 500 Lifetime XP per level, level 100 = «Легенда».
- Separate Lifetime XP and spendable XP balance; spending never reduces level.
- Weekly XP counter with automatic ISO-week reset.
- Auditable XP ledger with idempotency and anti-farming decay.
- Practical XP rewards: hints, Pinyin, slow audio, eliminate option, sentence start, explanations, examples, Smart Revision, Focus Mode, workshop pack, Role Play and Meeting Simulator.
- Four server-scored mini-games: Word Match, Listening Sprint, Phrase Builder, Find the Mistake.
- XP accrual for quizzes, scenarios, pair practice, course-day tests and final exam.
- Gentle Learning Nudge Engine with modes Off / Minimal / Normal / Active; escalating silence intervals and stop-after-three behavior until user returns.
- Browser notification support while the service is open and permission is granted.
- Admin content manager for custom English/Chinese terms by shop, topic, subtopic and CEFR level.
- CSV/XLSX bulk import.
- Admin analytics: per-user XP, level, term progress, recent practice and aggregate pilot KPIs.
- Environment-based bootstrap admin.

## Design constraints
- XP is motivational activity currency, not a language competency score.
- Core work functions are never locked behind XP.
- No punitive streak or loss of Lifetime XP.
- Manager-wide analytics is intentionally not exposed in this pilot until department scoping is added; global user analytics is Admin-only.
