# MGC Languages — Company Pilot v6.0.25

Корпоративный языковой сервис для сотрудников автопрома: **китайский (путунхуа / Standard Mandarin) + английский**, профессиональная терминология, реальные производственные ситуации, тесты, курс, игровая практика, связанные производственные сценарии и виртуальные смены.

**Текущий статус:** v6.0.25 Company Pilot на `main`.

## Ключевые возможности

- **2029 китайских терминов** в runtime.
- **2029 английских терминов** в runtime.
- Точный Chinese / English parity контролируется CI и LAN runtime smoke.
- **20 игровых механик** для автомобильной промышленности.
- **6 станций Factory Journey**: Штамповка → Кузов/сварка → Окраска → Сборка → Качество → Логистика.
- **3 Daily Missions** + Boss Shift.
- **7 компетенций Arcade Mastery**.
- Учебный / Смена / Эксперт + адаптивная сложность.
- Production Decision Chains и Dynamic Factory Scenarios.
- **Shift Simulation** из пяти связанных производственных эпизодов.
- **Personal Shift Analytics** с историей результатов под аккаунтом пользователя.
- Игровая backend-сессия ограничена **5 ответами**; Shift Simulation и аналитика не создают отдельный XP-контур.

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

## Словарь и языковой стандарт

Runtime содержит **2029 терминов на китайском и 2029 на английском**. Профессиональный слой включает производство, качество, логистику, кузов, компоненты, окраску, инженерные изменения и коммуникацию с поставщиками.

Основной китайский курс учит **путунхуа (普通话) — Standard Mandarin**. Для китайского используются иероглифы, pinyin, тоны, русский смысл и произношение. Диалекты остаются справочным материалом и не подменяют основной стандарт.

Ключевые данные:

```text
data/shop_expansion_v618.json
data/english_parallel_v618.json
data/v618_content_manifest.json
mgc/content_v618.py
```

## Factory Journey — v6.0.19

Пользователь проводит автомобиль через шесть производственных станций. Следующая станция открывается после завершения предыдущей; сохраняются лучший результат, общий прогресс и идеальные 5/5.

Journey работает поверх существующих backend game types и не дублирует игровой backend.

## Daily Missions, Boss Shift и Arcade Mastery — v6.0.20

Daily Missions формируют три короткие задачи:

1. цеховая миссия под подразделение;
2. новая или редко используемая механика;
3. тренировка слабого навыка.

Arcade Mastery переводит игровую практику в семь рабочих компетенций:

- Терминология;
- Аудирование;
- Производство;
- Качество;
- Логистика;
- Инженерия;
- Коммуникация.

Сервис предлагает следующую полезную игру по слабейшему приоритетному навыку.

## Production Game Depth — v6.0.21

Все 20 игр получили производственный контекст и уровни сложности:

- Учебный;
- Смена;
- Эксперт;
- Адаптивно.

В адаптивном режиме пять вопросов идут как **2 учебных → 2 сменных → 1 экспертный**. Используются сцены сварки, окраски, логистики, сборки, качества, безопасности, инженерии и рабочих коммуникаций.

## Production Decision Chains — v6.0.22

На уровнях Смена и Эксперт пользователь проходит трёхшаговые производственные решения до основной языковой задачи.

Восемь семейств:

- Andon / Line Stop;
- Quality Escalation;
- Material Shortage;
- Body Shop Containment;
- Paint Process Recovery;
- Safety Near Miss;
- Engineering Change;
- Supplier Escalation.

Неправильное решение показывает конкретное производственное последствие. Production judgement не начисляет отдельный XP.

## Dynamic Factory Scenarios — v6.0.23

Решения влияют на последующие события. Live Factory State учитывает suspect window, line-stop risk, material run-out, containment, restart readiness, configuration risk и качество supplier response.

Supplier Dialogue также ветвится: точные запросы с part / lot / quantity / owner / deadline / evidence дают лучший downstream outcome, чем общие эскалации.

## Shift Simulation — v6.0.24

Полная виртуальная смена состоит из пяти связанных эпизодов:

1. **08:00** — первые параллельные сигналы.
2. **09:35** — последствия ранних решений.
3. **11:20** — quality, material recovery и supplier control.
4. **14:05** — line stop / sequencing / supplier escalation.
5. **16:25** — финальные риски и shift handover.

На каждом эпизоде пользователь:

1. выбирает, какой инцидент разбирать первым;
2. принимает техническое/производственное решение;
3. выбирает рабочую формулировку на китайском или английском.

Невыбранные инциденты получают delay consequence и меняют Live Shift State.

### Live Shift State

В течение смены меняются:

- Стабильность линии;
- Защита качества;
- Material runway;
- Supplier control;
- Нагрузка команды.

### Shift Review

После пятого эпизода отдельно оцениваются:

- Production control;
- Prioritization;
- Production judgement;
- Language;
- общий результат смены.

Shift Simulation не добавляет `/api/games/*`, не начисляет отдельный XP и не меняет max-5 / anti-farm.

## Personal Shift Analytics — v6.0.25

Результат Shift Review теперь не исчезает после завершения одной смены. Он автоматически сохраняется под текущим корпоративным аккаунтом в PostgreSQL.

Для каждой смены фиксируются:

- общий результат;
- Production control;
- Prioritization;
- Production judgement;
- Language;
- изучаемый язык;
- финальные Line / Quality / Material / Supplier / Load;
- слабейшая компетенция;
- слабая производственная зона.

### Что видит пользователь

Блок `PERSONAL SHIFT ANALYTICS · v6.0.25` показывает:

- количество завершённых смен;
- последний результат;
- динамику относительно предыдущих смен;
- средние значения четырёх компетенций;
- повторяющуюся точку роста;
- производственный сигнал, который систематически проседает;
- последние смены;
- следующую рекомендуемую тренировку.

Рекомендации замыкают обучение в цикл:

- Production control → Shift Simulation + Quality Gate;
- Prioritization → Shift Simulation + Shift Incident;
- Production judgement → Quality Gate + Spec or NOK? + Shift Incident;
- Language → Dialogue Duel + Phrase Builder.

### Хранение и отказоустойчивость

v6.0.25 использует существующую таблицу `practice_results`, поэтому новая миграция БД не требуется. Записи user-scoped и доступны после входа с другого рабочего места.

При временной потере связи клиент держит небольшую pending-очередь и синхронизирует результат после восстановления доступа. Основным источником истории остаётся PostgreSQL.

API:

```text
POST /api/shift-simulations
GET  /api/shift-simulations/history
```

Маршруты аутентифицированы и входят в runtime route contract.

## Что входит в актуальный пилот

- китайский язык для автопрома с pinyin, тонами и произношением;
- английский для автомобильной промышленности;
- профессиональная терминология по цехам и функциям;
- Role Play и реальные рабочие ситуации;
- тесты, SRS, курс 30 дней и итоговый экзамен;
- 20 игр;
- Factory Journey;
- Daily Missions + Boss Shift;
- Arcade Mastery;
- Production Game Depth;
- Production Decision Chains;
- Dynamic Factory Scenarios;
- Shift Simulation;
- Personal Shift Analytics;
- XP, прогресс и anti-farm;
- роли User / Manager / Editor / Admin;
- OIDC/SSO, secure cookies, PostgreSQL, Alembic и RLS;
- Docker и one-click Company Pilot запуск.

## UX hardening

Сохранены release-specific UX hardening и пользовательские regression guards:

- упрощённый интерфейс без лишних декоративных блоков;
- Pinyin fallback для китайской терминологии;
- локальные/offline SVG для основных цехов;
- браузерные TTS-голоса с приоритетом **Natural / Neural / Online / Premium**;
- старый механизм произношения как fallback.

Ключевые файлы:

```text
static/frontend/pilot_ux_hardening.js
tests/v617_pilot_ux_regression_test.py
```

## GitHub Actions и тесты

На `main` работают два основных CI-контура:

1. `.github/workflows/ci.yml` — quality gate + реальный LAN PostgreSQL/Docker/Nginx smoke.
2. `.github/workflows/ci-v617-company-pilot.yml` — Company Pilot gate текущего пользовательского, словарного, игрового и симуляционного слоя.

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
```

CI контролирует 2029/2029 vocabulary parity, 20 game types, игровой UX, production depth, decision chains, dynamic factory state, Shift Simulation, Personal Shift Analytics, JavaScript syntax, runtime route contract и LAN runtime.

## One-click запуск Company Pilot

Windows:

```text
START_COMPANY_PILOT.bat
```

Launcher использует `scripts/start_company_pilot.ps1`, выполняет preflight, собирает Docker Compose, запускает сервис и проверяет readiness.

Корпоративный шаблон:

```text
.env.company-pilot.example
```

Основной preflight:

```bash
python scripts/company_pilot_preflight.py --strict-corporate
```

## Корпоративная безопасность

Для controlled company pilot предусмотрены OIDC/SSO, secure cookies, роли, PostgreSQL, RLS, readiness checks, governance терминологии и аудит. Финальная production-приёмка TLS/reverse proxy, backup/recovery, мониторинга и корпоративных политик остаётся задачей IT/Security.

---

**Pilot:** MGC Languages v6.0.25  
**Назначение:** корпоративное изучение китайского и английского языка для задач автомобильной промышленности.
