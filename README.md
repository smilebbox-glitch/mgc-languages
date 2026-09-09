# MGC Languages — Company Pilot v6.0.30

> **Актуальная версия репозитория: v6.0.30 (main).**  
> **Текущий продуктовый слой:** Stage E — Factory Journey 2.0.  
> **Текущий этап эксплуатации:** controlled real-VM pilot handoff. `v6.0.29 RC1` остаётся архивной Pilot Freeze baseline и больше не является текущей версией.

Корпоративный языковой сервис для сотрудников автопрома: **китайский (путунхуа / Standard Mandarin) + английский**, профессиональная терминология, реальные производственные ситуации, тесты, курс, игровая практика и производственные симуляции.

## Текущий состав пилота

- **2029 китайских терминов** и **2029 английских терминов** в runtime.
- Exact Chinese / English vocabulary parity.
- **20 Automotive Arcade game types**.
- Backend-игровая сессия ограничена **5 ответами**.
- Server-side anti-farm, XP/scoring и canonical answer path сохранены в v6.0.30.
- Factory Journey 2.0: семь связанных этапов Supplier → Logistics → Welding → Paint → Assembly → Quality → Engineering.
- Digital Vehicle progression и Factory Twin status.
- Daily Missions + Boss Shift + Arcade Mastery.
- Production Decision Chains, Dynamic Factory Scenarios и Shift Simulation.
- Personal Shift Analytics, Manager / Team Analytics и Top-10 Leaderboard.
- Adaptive Training Loop.
- UX / Accessibility / Performance hardening.
- PostgreSQL, Nginx, Docker Compose, LAN и Company Pilot deployment.
- Game World v6.0.30 с производственными сценами и process-specific automotive motion.

## v6.0.30 — Game World Expansion

v6.0.30 развивает Automotive Arcade из каталога упражнений в производственный Game World, сохраняя established learning/security contracts и единый server-authoritative scoring path.

### Production environments

Семь основных визуальных сред:

- Factory Hub;
- Assembly;
- Welding;
- Paint;
- Logistics;
- Quality;
- Engineering.

Все 20 игр сопоставлены с производственными сценами и уровнями сложности.

### Stage A — Production Gameplay Depth

Добавлена более глубокая производственная подача для сборки, сварки, окраски и логистики: движение автомобиля по линии, роботизированная ячейка сварки, surface inspection, intralogistics route и связанные визуальные производственные контексты.

### Stage B — Quality + Engineering

Добавлены CMM-style inspection, nominal/tolerance visualization, PASS / REWORK / HOLD context, а также drawing → BOM → subsystem digital-thread presentation.

### Stage C — Final Game Polish

Все 20 игр получили Mission Briefing, видимый five-step Mission Flow, нейтральный transition после ответа и итоговый Mission Complete, основанный только на server-derived final score.

### Stage D — Process-Specific Automotive Motion

Производственные сцены работают как конкретные операции, а не как общий анимированный фон:

- **Assembly:** установка детали, подход инструмента, torque verification, station beacon;
- **Welding:** последовательные weld points, robot-arm motion, weld flash, safety/containment behavior;
- **Paint:** spray-gun traverse, paint pass, optical scan, film-thickness visualization;
- **Logistics:** AGV/container movement Dock → Market → Line и replenishment/Kanban motion;
- **Quality:** CMM gantry/probe travel, actual-vs-nominal и tolerance-band visualization;
- **Engineering:** blueprint, drawing-to-BOM data packets, component hierarchy и release-state feedback;
- **Factory / communication:** Andon/takt board, communication pulse и control-room response.

### Stage E — Factory Journey 2.0

Stage E связывает существующие canonical games в одну производственную смену и не создаёт второй scoring/XP/API-контур.

Семь последовательных этапов:

1. **Supplier** — согласование актуальной ревизии чертежа до отгрузки.
2. **Logistics** — дефицит материала и replenishment routing до остановки линии.
3. **Welding** — остановка робота, safety interlock и containment language.
4. **Paint** — идентификация и сообщение о дефекте поверхности.
5. **Assembly** — крепление бампера, выбор инструмента и язык рабочей инструкции.
6. **Quality** — gap measurement, tolerance interpretation и disposition context.
7. **Engineering** — drawing/BOM mismatch и проверка актуальной ревизии.

**Digital Vehicle** показывает продвижение автомобиля через material preparation, BIW, paint, final assembly, quality verification и engineering release на основе уже существующего canonical game progress.

**Factory Twin** показывает состояние journey stages: trained / active / ready / pending.

English mode использует английские рабочие фразы с русским operational context. Chinese mode использует китайские фразы с pinyin и русским operational context.

Factory Journey 2.0 запускает только существующие `game-lab-v618` sessions и читает существующий `game-engagement-v618` progress. Нового game type, answer path, XP path, API endpoint или database migration не добавлено.

Полное описание текущего слоя: `CHANGELOG_v6.0.30.md`.

## Сохранённые контракты v6.0.30

- ровно 20 game types;
- максимум 5 ответов на игровую сессию;
- server-side anti-farm без альтернативного пути начисления;
- XP/scoring contract без второго контура;
- API contract сохранён;
- Stage E не добавляет database migration;
- PWA private/API cache isolation сохранён;
- `prefers-reduced-motion` поддерживается;
- Chinese localization не изменяет canonical answer values.

Машинно-проверяемая спецификация текущей версии:

```text
RELEASE_MANIFEST_v6.0.30.json
```

## Automotive Arcade — 20 игр

1. Word Match — термин ↔ перевод.
2. Listening Sprint — распознавание на слух.
3. Precision Check — точное значение.
4. Phrase Builder — сборка рабочей фразы.
5. Car Part Hotspot — детали автомобиля на интерактивной схеме.
6. Build the Car — технологическая последовательность.
7. Factory Router — маршрутизация по цехам.
8. Tool Selector — выбор инструмента.
9. Defect Detective — производственные дефекты.
10. Safety Spot — производственная безопасность.
11. Quality Gate — PASS / REWORK / HOLD.
12. Logistics Flow — материальный поток.
13. Kanban Challenge — пополнение.
14. Build the BOM — компонент ↔ подсистема.
15. Spec or NOK? — факт против допуска.
16. 10-Second Recall — быстрый ответ.
17. Memory Garage — пары.
18. Odd One Out — лишний термин.
19. Dialogue Duel — профессиональная рабочая реплика.
20. Shift Incident — решение производственной ситуации.

Backend contract хранится в `mgc/services/practice_games.py`: `MAX_GAME_ANSWERS = 5`, список `GAME_TYPES` содержит ровно 20 уникальных типов.

## Языковой стандарт

Основной китайский курс — **путунхуа (普通话) / Standard Mandarin**. Китайские учебные материалы используют иероглифы, pinyin, тоны, русский смысл и произношение. Диалекты используются только как справочный материал и не подменяют основной стандарт.

Ключевые данные:

```text
data/shop_expansion_v618.json
data/english_parallel_v618.json
data/v618_content_manifest.json
mgc/content_v618.py
```

## UX hardening

Сохранены обязательные пользовательские regression guards и UX hardening текущего пилота:

- упрощённая и читаемая pilot UI;
- Pinyin fallback для основной китайской автомобильной терминологии;
- локальные/offline SVG для профессиональных topic cards;
- браузерный TTS предпочитает голоса **Natural / Neural / Online / Premium** и снижает приоритет известных robotic fallback voices;
- игровые backend-сессии по-прежнему ограничены **5 ответами**;
- accessibility/performance hardening и `prefers-reduced-motion` остаются активными.

Ключевые guard-файлы:

```text
static/frontend/pilot_ux_hardening.js
tests/v617_pilot_ux_regression_test.py
```

## Историческая baseline v6.0.29 RC1

`v6.0.29 RC1` зафиксировал предыдущий Pilot Freeze и остаётся архивной baseline для сравнения и regression-control.

```text
RELEASE_MANIFEST_v6.0.29.json
```

v6.0.30 является первым post-RC product layer, которому разрешены новые visual runtime assets; текущий `RELEASE_MANIFEST_v6.0.30.json` содержит `freeze: false`.

## GitHub Actions и тесты

Основные gates включают:

```text
.github/workflows/ci.yml
.github/workflows/ci-v617-company-pilot.yml
.github/workflows/ci-v626-team-leaderboard.yml
.github/workflows/ci-v627-adaptive-training.yml
.github/workflows/ci-v628-ux-performance.yml
.github/workflows/ci-v629-release-candidate.yml
.github/workflows/ci-v630-game-world.yml
```

Main CI проверяет Python/API regressions, release contracts, JavaScript syntax и реальные Docker/LAN deployment paths, включая PostgreSQL + Nginx smoke.

## One-click Company Pilot

Windows:

```text
START_COMPANY_PILOT.bat
```

Launcher использует `scripts/start_company_pilot.ps1`, выполняет preflight, собирает Docker Compose, запускает сервис и проверяет readiness.

Корпоративный шаблон:

```text
.env.company-pilot.example
```

Preflight:

```bash
python scripts/company_pilot_preflight.py --strict-corporate
```

## Temporary shared VM pilot

До появления выделенного GPU-хоста сервис поддерживает общий CPU-only/no-AI тестовый контур вместе с `window-to-china`. Временный VM-профиль отключает server-side TTS/AI-heavy layer и публикует только hardened nginx ingress на TCP `8080`.

Общий operational runbook и порядок допуска пользователей находятся в соседнем репозитории `window-to-china`:

```text
CURRENT_VM_PILOT_HANDOFF.md
IT_DUAL_VM_QUICKSTART.md
VM_PILOT_ACCEPTANCE.md
VM_DAILY_OPERATIONS.md
```

Порядок допуска:

```text
FIREWALL -> START -> ACCEPTANCE -> READINESS -> DAILY OPS
```

## Пилотная change policy

Следующий приоритет — **реальная эксплуатация на тестовой VM**, а не дальнейшее добавление технических слоёв без подтверждённой потребности.

До получения фактической обратной связи от пользователей и IT изменения следует концентрировать на:

- blocker fixes;
- security fixes;
- VM/deployment compatibility;
- data integrity и recovery;
- подтверждённых UX/functional defects;
- test/acceptance corrections.

Новые продуктовые функции следует приоритизировать после реального пилотного цикла и измеримого пользовательского запроса.

## Корпоративная безопасность

Для controlled company pilot предусмотрены OIDC/SSO, secure cookies, роли, PostgreSQL, Alembic/RLS, readiness checks, content governance и аудит. Финальная production-приёмка TLS/reverse proxy, backup/recovery, мониторинга и корпоративных политик остаётся задачей IT/Security.

---

**Pilot:** MGC Languages v6.0.30 Stage E  
**Status:** Controlled real-VM pilot handoff / post-RC  
**Назначение:** корпоративное изучение китайского и английского языка для задач автомобильной промышленности.
