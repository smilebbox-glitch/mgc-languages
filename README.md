# MGC Languages — Company Pilot v6.0.20

Корпоративный языковой сервис для сотрудников автопрома: **китайский (путунхуа / Standard Mandarin) + английский**, профессиональная терминология, реальные рабочие сценарии, тесты, SRS и игровая практика.

**Текущий статус:** v6.0.20 Company Pilot на `main`.

## Ключевые цифры

- **2029 китайских терминов** в runtime.
- **2029 английских терминов** в runtime.
- **Точный паритет Chinese / English** контролируется CI и LAN runtime smoke.
- **20 различных игровых механик**.
- **6 станций Factory Journey**: Штамповка → Кузов/сварка → Окраска → Сборка → Качество → Логистика.
- **3 адаптивные Daily Missions** + **Boss Shift** после выполнения 3/3.
- **7 рабочих компетенций Arcade Mastery** с персональной картой навыков.
- Игровая сессия ограничена **5 ответами** на backend-уровне.

## Словарь v6.0.18–v6.0.20

Базовый корпус до расширения содержал 1735 китайских и 256 английских терминов. Для выравнивания английского словаря сформирован параллельный профессиональный English-layer из 1479 терминов.

В оба языка дополнительно добавлено по **240 автомобильных терминов**:

- **Окраска — +80** терминов на каждом языке;
- **Логистика — +80** терминов на каждом языке;
- **Кузов и компоненты — +80** терминов на каждом языке.

С учётом общего корпоративного слоя `experience.extra_terms` итоговый runtime содержит **2029 терминов на китайском и 2029 на английском**.

Данные и контроль:

```text
data/shop_expansion_v618.json
data/english_parallel_v618.json
data/v618_content_manifest.json
mgc/content_v618.py
tests/v618_content_games_regression_test.py
```

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

Игры имеют разные UI-механики: интерактивные зоны автомобиля, визуальные дефекты, производственный маршрут, инструменты, измерения, Kanban, BOM, память, таймер, аудио и рабочие сценарии.

Основные файлы:

```text
static/frontend/game_lab_v618.js
static/game_lab_v618.css
mgc/services/practice_games.py
```

## Factory Journey — v6.0.19

Новый слой объединяет отдельные игры в один автомобильный маршрут. Пользователь последовательно проходит шесть производственных станций:

1. **Штамповка** — Factory Router.
2. **Кузов / сварка** — Car Part Hotspot.
3. **Окраска** — Defect Detective.
4. **Сборка** — Build the Car.
5. **Качество** — Quality Gate.
6. **Логистика** — Logistics Flow.

Следующая станция открывается после завершения предыдущей. Интерфейс показывает лучший результат по станции, общий процент маршрута и количество идеальных 5/5.

Factory Journey работает поверх существующих 20 backend game types, поэтому не дублирует игровую логику и сохраняет серверные ограничения XP/anti-farm.

Файлы:

```text
static/frontend/factory_journey_v619.js
static/factory_journey_v619.css
tests/v619_factory_journey_test.py
CHANGELOG_v6.0.19.md
BUILD_INFO_v6.0.19.txt
```

## Daily Missions и Boss Shift — v6.0.20

Чтобы игры не превращались в статичный каталог, добавлен ежедневный игровой слой:

1. **Цеховая миссия** — игра под отдел/цех пользователя.
2. **Новая механика** — режим, который пользователь ещё не проходил или проходил редко.
3. **Точка роста** — восстановление слабого навыка по истории результатов.

После выполнения 3/3 открывается **Boss Shift** — короткая тематическая сменная задача. Маршрутизация учитывает подразделение: окраска получает Defect Detective, логистика — Logistics Flow, кузов и компоненты — Car Part Hotspot, сборка — Build the Car, качество — Quality Gate, R&D — Build the BOM, закупки — Dialogue Duel.

Файлы:

```text
static/frontend/arcade_missions_v620.js
static/arcade_missions_v620.css
tests/v620_arcade_missions_test.py
BUILD_INFO_v6.0.20.txt
```

## Персональная игровая практика

Сохранён engagement-layer v6.0.18:

- рекомендации игр по отделу пользователя;
- Game of the Day;
- Arcade Passport — сколько из 20 механик уже попробовано;
- лучший результат по каждой игре;
- активные дни и завершённые игровые сессии.

Для сотрудников окраски выше поднимаются Defect Detective / Spec Check / Tool Selector / Safety Spot; для логистики — Logistics Flow / Kanban / Factory Router / Rapid Recall; для кузова и компонентов — Hotspot / BOM / технологические последовательности / дефекты.

## Arcade Mastery — карта навыков

Игровые результаты теперь переводятся в **7 рабочих компетенций**, чтобы сотрудник видел не только XP, но и развитие конкретных навыков:

1. Терминология.
2. Аудирование.
3. Производство.
4. Качество.
5. Логистика.
6. Инженерия.
7. Коммуникация.

Mastery-score на 75% учитывает лучший результат в релевантных играх и на 25% — охват разных механик. Для каждого отдела выделяются приоритетные компетенции: например, для окраски — качество / производство / терминология, для логистики — логистика / коммуникация / терминология, для кузова и компонентов — инженерия / производство / качество.

Сервис автоматически находит слабейший приоритетный навык и предлагает **следующую наиболее полезную игру**. Добавлены уровни ROOKIE → DEVELOPING → OPERATOR → SPECIALIST → EXPERT → MASTER и достижения за реальный прогресс. Запуски из карты навыков идут через тот же Arcade Passport и не создают отдельный XP-контур.

Файлы:

```text
static/frontend/arcade_mastery_v620.js
static/arcade_mastery_v620.css
tests/v620_arcade_mastery_test.py
```

## Что входит в актуальный пилот

- китайский язык для автопрома с пиньинем, тонами и произношением;
- английский язык для автомобильной промышленности;
- профессиональная терминология по цехам и функциям;
- реальные рабочие ситуации и Role Play;
- тесты, SRS, курс 30 дней, итоговый экзамен;
- 20 игр + Factory Journey + Daily Missions + Boss Shift + Arcade Mastery;
- XP, прогресс и anti-farm;
- фраза дня, план на сегодня, быстрый доступ и подборки терминов;
- роли User / Manager / Editor / Admin;
- OIDC/SSO, secure cookies, PostgreSQL, Alembic и RLS;
- Docker и one-click Company Pilot запуск.

## UX hardening

Сохранены улучшения v6.0.17:

- упрощённый интерфейс без лишних декоративных блоков;
- Pinyin fallback для китайских автомобильных терминов;
- локальные/offline SVG по сборке, сварке, окраске, штамповке, качеству и логистике;
- более естественные браузерные TTS-голоса с приоритетом Natural / Neural / Online / Premium;
- старый механизм произношения остаётся fallback.

Release-specific UX hardening и его regression guard:

```text
static/frontend/pilot_ux_hardening.js
tests/v617_pilot_ux_regression_test.py
```

## GitHub Actions и тесты

На `main` работают два основных CI-контура:

1. `.github/workflows/ci.yml` — quality gate + LAN PostgreSQL/Docker/Nginx smoke.
2. `.github/workflows/ci-v617-company-pilot.yml` — Company Pilot gate, проверяющий текущий игровой и словарный слой до v6.0.20.

Ключевые regression-тесты:

```text
tests/v617_pilot_ux_regression_test.py
tests/v618_content_games_regression_test.py
tests/v619_factory_journey_test.py
tests/v620_arcade_missions_test.py
tests/v620_arcade_mastery_test.py
```

CI контролирует словарный паритет 2029/2029, 20 game types, Car Part Hotspot, персональную аркаду, Factory Journey, Daily Missions, Boss Shift, Arcade Mastery, JavaScript syntax и реальный LAN runtime.

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

**Pilot:** MGC Languages v6.0.20  
**Назначение:** корпоративное изучение китайского и английского языка для задач автомобильной промышленности.
