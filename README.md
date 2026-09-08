# MGC Languages — Company Pilot v6.0.29 RC1

> **Актуальная версия репозитория: v6.0.29 RC1 (main).** README синхронизирован с текущим пилотом и последними исправлениями, включая улучшенный natural-voice TTS.

Корпоративный языковой сервис для сотрудников автопрома: **китайский (путунхуа / Standard Mandarin) + английский**, профессиональная терминология, реальные производственные ситуации, тесты, курс, игровая практика и связанные производственные симуляции.

**Текущий статус:** `v6.0.29 RC1` на `main`, функциональный состав **Pilot Freeze**.

## Зафиксированный состав RC1

- **2029 китайских терминов** и **2029 английских терминов** в runtime.
- Exact Chinese / English vocabulary parity.
- **20 Automotive Arcade game types**.
- Backend-игровая сессия ограничена **5 ответами**.
- Anti-farm и XP-контур не менялись в v6.0.29.
- 6 станций Factory Journey: Штамповка → Кузов/сварка → Окраска → Сборка → Качество → Логистика.
- Daily Missions + Boss Shift + Arcade Mastery.
- Production Game Depth и адаптивная сложность.
- Production Decision Chains и Dynamic Factory Scenarios.
- Shift Simulation из пяти связанных производственных эпизодов.
- Personal Shift Analytics с историей под аккаунтом пользователя.
- Manager / Team Analytics и Top-10 Leaderboard.
- Adaptive Training Loop v6.0.27.
- UX / Accessibility / Performance hardening v6.0.28.
- PostgreSQL, Nginx, Docker Compose, LAN и Company Pilot deployment.

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

## Производственные учебные слои

### v6.0.19 — Factory Journey

Автомобиль проходит шесть производственных станций. Следующая станция открывается после предыдущей; Journey работает поверх существующих backend game types и не создаёт новый игровой backend.

### v6.0.20 — Daily Missions / Boss Shift / Arcade Mastery

Ежедневные миссии комбинируют подразделение, игровую механику и слабую компетенцию. Arcade Mastery отслеживает терминологию, аудирование, производство, качество, логистику, инженерию и коммуникацию.

### v6.0.21 — Production Game Depth

20 игр используют производственные сцены сварки, окраски, логистики, сборки, качества, безопасности и инженерии. Доступны Учебный / Смена / Эксперт / Адаптивно.

### v6.0.22 — Production Decision Chains

На уровнях Смена и Эксперт пользователь принимает производственные решения до языкового задания: Andon/Line Stop, Quality Escalation, Material Shortage, Body Shop, Paint, Safety, Engineering Change и Supplier Escalation. Production judgement не создаёт отдельный XP.

### v6.0.23 — Dynamic Factory Scenarios

Предыдущие решения изменяют последующие условия: suspect window, line-stop risk, material run-out, containment, restart readiness, configuration risk и supplier response.

### v6.0.24 — Shift Simulation

Пять связанных эпизодов: 08:00, 09:35, 11:20, 14:05 и 16:25. На каждом пользователь выбирает приоритет, принимает техническое решение и выбирает рабочую формулировку. Невыбранные инциденты получают delay consequence.

Live Shift State отслеживает стабильность линии, защиту качества, material runway, supplier control и нагрузку команды. Shift Simulation не добавляет `/api/games/*` и не меняет max-5 / anti-farm.

### v6.0.25 — Personal Shift Analytics

Shift Review сохраняется под корпоративным аккаунтом пользователя в PostgreSQL. Доступны история, тренд, повторяющаяся точка роста, слабая производственная область и следующая рекомендуемая тренировка.

```text
POST /api/shift-simulations
GET  /api/shift-simulations/history
```

### v6.0.26 — Manager / Team Analytics + Top-10

Руководитель видит department-scoped агрегаты обучения, а не HR-рейтинг. Top-10 сортируется по score, затем по серверному времени, при этом на сотрудника учитывается лучшая попытка.

```text
GET /api/manager/shift-analytics
GET /api/leaderboards/games/{game_type}
GET /api/leaderboards/shifts
```

### v6.0.27 — Adaptive Training Loop

Персональная тренировка использует накопленные результаты и направляет пользователя в слабейшие практические области без создания нового game type или отдельного XP-контура.

### v6.0.28 — UX / Accessibility / Performance Polish

Добавлены skip-link, focus management, ARIA states, keyboard navigation, reduced-motion/high-contrast support и `content-visibility:auto` для тяжёлых offscreen-блоков. Старый DOM hardening больше не выполняет полный scan документа на каждую mutation; изменения пакетируются через `requestAnimationFrame`.

## v6.0.29 — Release Candidate / Pilot Freeze

v6.0.29 не добавляет новую пользовательскую функцию. Это release-control слой, который фиксирует текущий пилот как **RC1**.

Машинно-проверяемая спецификация:

```text
RELEASE_MANIFEST_v6.0.29.json
```

Guard:

```bash
python scripts/release_candidate_guard.py --json
```

Guard проверяет:

- 2029/2029 vocabulary parity;
- точный список 20 game types;
- `MAX_GAME_ANSWERS == 5`;
- frozen frontend `requiredModules`;
- `pilotCandidate: v6.0.29`;
- обязательные critical/deployment files;
- отсутствие нового v6.0.29 runtime JS/CSS слоя.

После RC1 без явного снятия freeze допускаются только blocker/security/deployment fixes, исправления документации и release/test gate fixes. Новые game types, frontend feature modules, migrations, XP paths и продуктовые функции запрещены manifest-контрактом.

## UX hardening

Сохранены release-specific **UX hardening** и пользовательские regression guards:

- упрощённый интерфейс;
- Pinyin fallback для китайской терминологии;
- локальные/offline SVG;
- браузерные TTS-голоса с приоритетом **Natural / Neural / Online / Premium**;
- старый механизм произношения как fallback;
- игровые backend-сессии ограничены **5 ответами**.

Ключевые файлы:

```text
static/frontend/pilot_ux_hardening.js
tests/v617_pilot_ux_regression_test.py
```

## GitHub Actions и тесты

Основные release gates:

```text
.github/workflows/ci.yml
.github/workflows/ci-v617-company-pilot.yml
.github/workflows/ci-v626-team-leaderboard.yml
.github/workflows/ci-v627-adaptive-training.yml
.github/workflows/ci-v628-ux-performance.yml
.github/workflows/ci-v629-release-candidate.yml
```

Ключевые regressions:

```text
tests/v617_pilot_ux_regression_test.py
tests/v618_content_games_regression_test.py
tests/v619_factory_journey_test.py
tests/v620_arcade_missions_test.py
tests/v620_arcade_mastery_test.py
tests/v621_game_depth_test.py
tests/v622_decision_chains_test.py
tests/v623_dynamic_factory_test.py
tests/v624_shift_simulation_test.py
tests/v625_shift_analytics_test.py
tests/v626_team_leaderboard_test.py
tests/v627_adaptive_training_test.py
tests/v628_ux_performance_test.py
tests/v629_release_candidate_test.py
```

Main CI выполняет Python/API regressions, release candidate guard, JavaScript syntax и реальный LAN PostgreSQL + Nginx + Docker Compose smoke.

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

## Корпоративная безопасность

Для controlled company pilot предусмотрены OIDC/SSO, secure cookies, роли, PostgreSQL, Alembic/RLS, readiness checks, content governance и аудит. Финальная production-приёмка TLS/reverse proxy, backup/recovery, мониторинга и корпоративных политик остаётся задачей IT/Security.

---

**Pilot:** MGC Languages v6.0.29 RC1  
**Status:** Pilot Freeze  
**Назначение:** корпоративное изучение китайского и английского языка для задач автомобильной промышленности.
