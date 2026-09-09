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

## Chinese Game Localization Audit

The Chinese Automotive Arcade surface was audited after Stage C because several hard-coded production and engineering labels still appeared in English even when the selected learning language was Chinese.

- All 20 game titles now receive a Chinese primary title with pinyin on the Chinese game surface.
- Quality statuses are presented as 合格 / 返工 / 暂停 instead of PASS / REWORK / HOLD.
- Logistics Flow sequences are presented in Chinese, including receiving, scanning, put-away, replenishment, picking, customs, transport and shortage-response steps.
- Build the BOM presents automotive components in Chinese instead of leaking English component names.
- Spec or NOK? presents 间隙 / 面差 / 扭矩 / 漆膜厚度 / 压力 instead of Gap / Flush / Torque / Film thickness / Pressure.
- Stage A/B/C visual labels for assembly, welding, paint, logistics, quality, engineering and Mission UI are localized for Chinese mode.
- Stage D process-motion labels are also localized for Chinese mode.
- The localization layer is presentation-only and reversible when switching back to English; canonical answer values are untouched so order-game and server scoring contracts remain unchanged.

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
