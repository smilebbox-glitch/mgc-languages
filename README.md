# MGC Languages — Company Pilot v6.0.24

Корпоративный языковой сервис для сотрудников автопрома: **китайский (путунхуа / Standard Mandarin) + английский**, профессиональная терминология, реальные производственные ситуации, тесты, курс, игровая практика и сменные симуляции.

**Текущий статус:** v6.0.24 Company Pilot на `main`.

## Ключевые цифры

- **2029 китайских терминов** в runtime.
- **2029 английских терминов** в runtime.
- **Точный паритет Chinese / English** контролируется CI и LAN runtime smoke.
- **20 различных игровых механик**.
- **6 станций Factory Journey**: Штамповка → Кузов/сварка → Окраска → Сборка → Качество → Логистика.
- **3 адаптивные Daily Missions** + **Boss Shift**.
- **7 рабочих компетенций Arcade Mastery**.
- **3 производственных уровня сложности** + адаптивный режим.
- **8 семейств Production Decision Chains / Dynamic Factory Scenarios**.
- **5 связанных эпизодов Shift Simulation**, по 3 решения на эпизод.
- Игровая backend-сессия ограничена **5 ответами**; новый симуляционный слой не создаёт отдельный XP-контур.

## Automotive Arcade — 20 игр

1. Word Match — термин ↔ перевод.
2. Listening Sprint — распознавание на слух.
3. Precision Check — точное значение.
4. Phrase Builder — сборка рабочей фразы.
5. Car Part Hotspot — найти деталь на интерактивной схеме автомобиля.
6. Build the Car — технологическая последовательность.
7. Factory Router — отправить термин в правильный цех.
8. Tool Selector — выбрать инструмент под задачу.
9. Defect Detective — определить производственный дефект.
10. Safety Spot — найти опасность на рабочем месте.
11. Quality Gate — PASS / REWORK / HOLD.
12. Logistics Flow — собрать материальный поток.
13. Kanban Challenge — решение о пополнении.
14. Build the BOM — связать компонент с подсистемой.
15. Spec or NOK? — сравнить факт с допуском.
16. 10-Second Recall — быстрый ответ под таймер.
17. Memory Garage — карточки-пары.
18. Odd One Out — найти лишний термин.
19. Dialogue Duel — выбрать профессиональную реплику.
20. Shift Incident — решение в реальной сменной ситуации.

Игры используют интерактивные зоны автомобиля, визуальные дефекты, производственные маршруты, инструменты, измерения, Kanban, BOM, память, таймер, аудио и рабочие сценарии.

## Словарь

Базовый корпус был расширен и выровнен между языками. В runtime сейчас **2029 терминов на китайском и 2029 на английском**. В оба языка дополнительно добавлены профессиональные термины по окраске, логистике, кузову и компонентам.

Основные файлы:

```text
data/shop_expansion_v618.json
data/english_parallel_v618.json
data/v618_content_manifest.json
mgc/content_v618.py
tests/v618_content_games_regression_test.py
```

## Factory Journey — v6.0.19

Пользователь последовательно проходит шесть автомобильных производственных станций:

1. Штамповка.
2. Кузов / сварка.
3. Окраска.
4. Сборка.
5. Качество.
6. Логистика.

Следующая станция открывается после завершения предыдущей. Показываются лучший результат, общий прогресс и идеальные 5/5. Journey использует существующие 20 backend game types и не создаёт отдельный XP-контур.

## Daily Missions и Boss Shift — v6.0.20

Ежедневный слой формирует три короткие миссии:

1. цеховая миссия под подразделение пользователя;
2. новая или редко используемая механика;
3. точка роста по слабому навыку.

После выполнения 3/3 открывается Boss Shift. Маршрутизация учитывает отдел: окраска, логистика, кузов, сборка, качество, R&D и закупки получают разные игровые приоритеты.

## Arcade Mastery — v6.0.20

Результаты переводятся в 7 рабочих компетенций:

1. Терминология.
2. Аудирование.
3. Производство.
4. Качество.
5. Логистика.
6. Инженерия.
7. Коммуникация.

Сервис определяет слабейший приоритетный навык, рекомендует следующую игру и показывает уровни ROOKIE → DEVELOPING → OPERATOR → SPECIALIST → EXPERT → MASTER.

## Production Game Depth — v6.0.21

Все 20 игр получили дополнительный производственный слой:

- Учебный / Смена / Эксперт + Адаптивно;
- адаптивная последовательность 5 вопросов: **2 учебных → 2 сменных → 1 экспертный**;
- отдельные сцены сварки, окраски, логистики, сборки, качества, безопасности, инженерии и рабочих коммуникаций;
- более детальная схема автомобиля в Car Part Hotspot;
- уменьшение подсказок в экспертном режиме.

Backend max-5, XP и anti-farm не изменялись.

## Production Decision Chains — v6.0.22

На уровнях Смена и Эксперт языковая задача может начинаться с трёх последовательных производственных решений. Неправильный выбор показывает конкретное последствие, а после каждого шага даётся полезная рабочая фраза на изучаемом языке.

Восемь семейств:

- Andon / Line Stop;
- Quality Escalation;
- Material Shortage;
- Body Shop Containment;
- Paint Process Recovery;
- Safety Near Miss;
- Engineering Change;
- Supplier Escalation.

Production judgement не начисляет отдельный XP.

## Dynamic Factory Scenarios — v6.0.23

Решения из v6.0.22 теперь меняют **состояние следующего шага**.

Live Factory State может отражать:

- число автомобилей/кузовов в suspect window;
- риск повторного line stop;
- material run-out;
- containment и process evidence;
- restart readiness;
- engineering configuration risk;
- качество supplier response.

Supplier Dialogue также ветвится: размытая эскалация вызывает уточняющий ответ, а точная формулировка с part / lot / quantity / owner / deadline / evidence ускоряет переход к traceability, containment и подтверждённому ETA.

## Shift Simulation — v6.0.24

Shift Simulation объединяет производственную логику и язык в полноценную виртуальную смену из **5 связанных эпизодов**:

1. **08:00** — первые параллельные сигналы.
2. **09:35** — последствия ранних решений.
3. **11:20** — качество, material recovery и supplier control.
4. **14:05** — line stop / sequencing / supplier escalation в зависимости от состояния смены.
5. **16:25** — финальные риски и shift handover.

На каждом эпизоде пользователь:

1. выбирает, какой из одновременно активных инцидентов разбирать первым;
2. принимает техническое/производственное решение;
3. выбирает рабочую формулировку на китайском или английском.

Невыбранные инциденты получают **delay consequence** и ухудшают Live Shift State. Поэтому пользователь тренирует реальную приоритизацию, а не независимые тестовые вопросы.

### Live Shift State

В течение смены меняются:

- **Стабильность линии**;
- **Защита качества**;
- **Material runway**;
- **Supplier control**;
- **Нагрузка команды**.

Следующие эпизоды ветвятся по предыдущим решениям и этим значениям. Например, корректный supplier expedite ведёт к traceability, отсутствие recovery — к material run-out; корректный torque containment — к first-off, плохая реакция — к Quality Gate hold; накопленные риски могут привести к line stop.

### Языковая практика

В китайском режиме пользователь видит:

- иероглифы;
- pinyin;
- русский смысл;
- оценку точности рабочей формулировки.

В английском режиме используются shop-floor English и русский смысл.

### Shift Review

После пятого эпизода отдельно оцениваются:

- **Production control**;
- **Prioritization**;
- **Production judgement**;
- **Language**;
- общий результат смены.

Пользователь также получает конечный Live Shift State, основную точку роста и языковой разбор с более профессиональными формулировками.

Shift Simulation не добавляет `/api/games/*`, не начисляет отдельный XP, не изменяет серверный max-5 и anti-farm.

Файлы:

```text
static/frontend/shift_simulation_v624.js
static/shift_simulation_v624.css
tests/v624_shift_simulation_test.py
CHANGELOG_v6.0.24.md
BUILD_INFO_v6.0.24.txt
```

## Что входит в актуальный пилот

- китайский язык для автопрома с пиньинем, тонами и произношением;
- английский язык для автомобильной промышленности;
- профессиональная терминология по цехам и функциям;
- реальные рабочие ситуации и Role Play;
- тесты, SRS, курс 30 дней, итоговый экзамен;
- 20 игр;
- Factory Journey;
- Daily Missions + Boss Shift;
- Arcade Mastery;
- Production Game Depth;
- Production Decision Chains;
- Dynamic Factory Scenarios;
- Shift Simulation;
- XP, прогресс и anti-farm;
- роли User / Manager / Editor / Admin;
- OIDC/SSO, secure cookies, PostgreSQL, Alembic и RLS;
- Docker и one-click Company Pilot запуск.

## UX hardening

Сохранены:

- упрощённый интерфейс без лишних декоративных блоков;
- Pinyin fallback для китайских автомобильных терминов;
- локальные/offline SVG по сборке, сварке, окраске, штамповке, качеству и логистике;
- более естественные браузерные TTS-голоса с приоритетом Natural / Neural / Online / Premium;
- старый механизм произношения как fallback.

## GitHub Actions и тесты

На `main` работают два основных CI-контура:

1. `.github/workflows/ci.yml` — quality gate + LAN PostgreSQL/Docker/Nginx smoke.
2. `.github/workflows/ci-v617-company-pilot.yml` — Company Pilot gate текущего словарного, игрового и симуляционного слоя до v6.0.24.

Ключевые regression-тесты:

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
```

CI контролирует словарный паритет 2029/2029, 20 game types, игровой UX, production depth, decision chains, dynamic factory state, Shift Simulation, JavaScript syntax и реальный LAN runtime.

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

## Китайский стандарт

Основной курс учит **путунхуа (普通话) — Standard Mandarin**. Диалекты используются только как справочный материал и не подменяют основной стандарт обучения.

## Корпоративная безопасность

Для controlled company pilot предусмотрены OIDC/SSO, secure cookies, роли, PostgreSQL, RLS, readiness checks, governance терминологии и аудит. Финальная production-приёмка по TLS/reverse proxy, backup/recovery, мониторингу и корпоративным политикам остаётся задачей IT/Security.

---

**Pilot:** MGC Languages v6.0.24  
**Назначение:** корпоративное изучение китайского и английского языка для задач автомобильной промышленности.
