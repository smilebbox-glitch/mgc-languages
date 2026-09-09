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
