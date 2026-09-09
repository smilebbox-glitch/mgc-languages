# MGC Languages v6.0.30 — Game World Expansion

## Scope

v6.0.30 moves the Automotive Arcade from a flat exercise catalogue to a production-themed Game World while preserving the established learning and security contracts.

## Added

- Seven visual production environments: Factory Hub, Assembly, Welding, Paint, Logistics, Quality and Engineering.
- Scene mapping for all 20 Automotive Arcade game types.
- Difficulty labels: Базовый, Средний, Продвинутый.
- Animated conveyor, vehicle, industrial robots, scanner and contextual particles.
- Production HUD with zone, difficulty, language and mission context.
- Modern card motion, question transitions and progress treatment.
- Mobile-adaptive Game World layout.
- `prefers-reduced-motion` support.

## Stage A — Production Gameplay Depth

The first production-depth layer keeps canonical answer controls and server scoring intact while making the selected game mechanic feel tied to a real automotive process.

- **Assembly:** animated operation flow (Body → Trim → Chassis → Final), vehicle movement along the line, enhanced Car Part Hotspot, Build the Car sequence and Tool Selector presentation.
- **Welding:** robot-cell visualization, pulsing weld points, sparks and enhanced Safety Spot / Shift Incident context.
- **Paint:** optical surface scan with scratch, paint-run and orange-peel inspection cues around Defect Detective.
- **Logistics:** animated intralogistics route (Dock → Supermarket → Line side), tugger movement and enhanced Factory Router / Logistics Flow / Kanban context.
- Stage A covers 12 existing game types without adding a second answer, API, XP or scoring path.
- Scene interaction feedback is visual only and observes the canonical game controls.

## Stage B — Quality + Engineering

Stage B deepens the professional engineering side of the arcade while retaining the same canonical game session and scoring path.

- **Quality:** digital CMM-style inspection station, animated probe, nominal/tolerance visualization and PASS / REWORK / HOLD disposition context.
- **Precision Check:** quality-lab context around exact terminology and decision accuracy.
- **Quality Gate:** visual disposition station tied to the existing measurement game.
- **Spec or NOK?:** tolerance-centered presentation around the existing spec comparison mechanic.
- **Engineering:** drawing → BOM → subsystem digital-thread scene with revision status and structured component hierarchy.
- **Build the BOM:** existing BOM mechanic receives engineering drawing and hierarchy context without changing answers.
- **Odd One Out:** engineering classification context for functional-group vocabulary.
- Stage B covers 5 existing game types without adding a second answer, API, XP or scoring path.

## Stage C — Final Game Polish

Stage C closes the Game World UX loop across all 20 game types while preserving server-authoritative scoring.

- Per-game **Mission Briefing** onboarding before the first operation of a new session.
- Five-step **Mission Flow** rail that makes the max-five session visible at all times.
- Neutral **«Ответ зафиксирован»** transition between operations; it never claims per-answer correctness before the server finishes scoring.
- Server-derived **Mission Complete** result hero with perfect / strong / developing presentation based only on the canonical final score.
- Stronger press, focus and question-entry micro-interactions.
- Mobile sticky progress, larger touch targets and compact result composition.
- `prefers-reduced-motion` remains supported.
- Stage C covers all 20 game types without adding a second answer, API, XP or scoring path.

## Stage D — Process-Specific Motion

Stage D makes the production scenes behave like actual automotive operations instead of generic ambient animation. The motion reacts to canonical game interaction but remains neutral until server scoring finishes.

- **Assembly:** part installation, tool approach, torque verification, station beacon and operation-progress motion.
- **Welding:** sequential spot-weld illumination, robot-arm motion, weld flash and safety-interlock / containment beacon behavior.
- **Paint:** spray-gun traverse, paint-cloud pass, optical scan and film-thickness visualization.
- **Logistics:** AGV/container movement through Dock → Market → Line, plus Kanban/replenishment process motion.
- **Quality:** CMM gantry/probe travel, actual-vs-nominal readout and animated tolerance-band measurement.
- **Engineering:** animated blueprint, drawing-to-BOM data packets, component hierarchy cascade and release-state feedback.
- **Factory / communication:** Andon/takt board, communication-node pulse and rapid decision/control-room response.
- All 20 games now receive a distinct process-motion profile while continuing to use the canonical five-answer session and server scoring path.
- Process labels are localized in Chinese mode; switching language does not alter canonical answer values.
- Stage D remains presentation-only and contains no API, XP or alternate answer submission path.

## Stage E — Factory Journey 2.0

Stage E turns the existing factory route into a connected shift simulation instead of another list of exercises. It orchestrates existing canonical games and reads their existing completion/best-score progress; it does not add a second scoring system.

- Seven linked shift stages: **Supplier → Logistics → Welding → Paint → Assembly → Quality → Engineering**.
- Each stage starts with a realistic automotive production incident and a concrete communication task.
- Supplier incident covers drawing-revision approval before shipment.
- Logistics incident covers material shortage and replenishment routing before a line stop.
- Welding incident covers robot stop, safety interlock and containment language.
- Paint incident covers surface-defect identification and reporting.
- Assembly incident covers bumper fastening, tool selection and work-instruction language.
- Quality incident covers gap measurement, tolerance interpretation and disposition context.
- Engineering incident covers drawing/BOM mismatch and current revision verification.
- A **Digital Vehicle** progressively moves through material preparation, BIW, paint, final assembly, quality verification and engineering release based on canonical game completion.
- A **Factory Twin** status panel shows which journey stages are trained, active, ready or pending.
- English mode presents English incident language with Russian operational context; Chinese mode presents Chinese incident language with pinyin and Russian operational context.
- Factory Journey 2.0 launches only existing `game-lab-v618` sessions and reads `game-engagement-v618` progress.
- No new game type, answer path, XP path, API endpoint or database migration is introduced.

## Chinese Game Localization Audit

The Chinese Automotive Arcade surface was audited after Stage C because several hard-coded production and engineering labels still appeared in English even when the selected learning language was Chinese.

- All 20 game titles now receive a Chinese primary title with pinyin on the Chinese game surface.
- Quality statuses are presented as 合格 / 返工 / 暂停 instead of PASS / REWORK / HOLD.
- Logistics Flow sequences are presented in Chinese, including receiving, scanning, put-away, replenishment, picking, customs, transport and shortage-response steps.
- Build the BOM presents automotive components in Chinese instead of leaking English component names.
- Spec or NOK? presents 间隙 / 面差 / 扭矩 / 漆膜厚度 / 压力 instead of Gap / Flush / Torque / Film thickness / Pressure.
- Stage A/B/C visual labels for assembly, welding, paint, logistics, quality, engineering and Mission UI are localized for Chinese mode.
- Stage D process-motion labels are also localized for Chinese mode.
- Stage E Factory Journey incidents, route labels and shift-status copy are localized in Chinese and include pinyin for the main learning phrases.
- The localization layer is presentation-only and reversible when switching back to English; canonical answer values are untouched so order-game and server scoring contracts remain unchanged.

## Chinese Learning Surface + Level Uniqueness

The Chinese track is now consistent beyond the game scene itself.

- Arcade Mastery / game profile labels and tier names are localized for Chinese mode.
- XP and progress surfaces no longer leak English labels while Chinese is selected.
- Quiz questions continue to show pinyin, and Chinese answer choices now receive server-derived pinyin where the choice itself is Chinese.
- Role Play keeps Chinese questions/options as the primary learning text with pinyin and Russian meaning support.
- The 30-day course keeps Chinese terms and pronunciation visible throughout the Chinese track.
- A learning-content projection enforces **one visible term = one CEFR level**. If the same visible term exists in several levels, the lowest existing level (A1 → C1) becomes canonical and the richest row in that level is shown.
- Duplicate filtering happens only in the learning projection. The raw 2029/2029 corpus, stable term IDs, archived release parity, XP/scoring and database schema are unchanged.

## Executive Visual System

The product now receives a final presentation-only design layer intended for leadership demos and day-to-day corporate use.

- Unified premium visual language across login, shell/navigation, home dashboard, topics, terms, tests, Automotive Arcade, XP/mastery and Factory Journey 2.0.
- Glass-like top navigation, deep automotive sidebar, stronger spacing/typography hierarchy and a restrained blue/cyan industrial palette.
- Leadership-facing hero redesigned as a dark executive automotive surface with controlled grid/light effects and a stronger product focal point.
- Cards, topic tiles, term cards and analytical panels share one radius, border, depth and hover system instead of looking like separate modules.
- Automotive Arcade cards receive clearer hierarchy, stronger game identity and more premium interaction states without changing game content.
- Factory Journey 2.0 receives deeper contrast and richer digital-twin framing while keeping the existing journey logic unchanged.
- Authentication gets the same corporate visual language so the first impression matches the product after login.
- Responsive behavior and `prefers-reduced-motion` remain first-class requirements.
- The layer is CSS-only: no API, scoring, XP, language, database or business-logic path is changed.

## Preserved contracts

- 20 game types.
- Maximum five answers per session.
- Server-side anti-farm logic unchanged.
- XP/scoring paths unchanged.
- API contract unchanged.
- No database migration.
- PWA private/API cache isolation unchanged.

## Release transition

v6.0.29 RC1 remains the archived pilot-freeze baseline. v6.0.30 is the first post-RC product layer permitted to add visual runtime assets and is not frozen (`freeze: false`).