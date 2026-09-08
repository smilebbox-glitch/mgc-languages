# v6.0.25 — Personal Shift Analytics

## Цель

Превратить результат одной виртуальной смены в накопительный персональный контур обучения: сервис должен помнить предыдущие Shift Simulation под корпоративным аккаунтом, показывать повторяющиеся слабые места и направлять пользователя в следующую наиболее полезную тренировку.

## Что изменилось

### История смен под аккаунтом

После завершения Shift Simulation результат автоматически сохраняется в PostgreSQL под текущим пользователем.

Для каждой завершённой смены сохраняются:

- общий Shift Review score;
- Production control;
- Prioritization;
- Production judgement;
- Language;
- изучаемый язык;
- финальные значения Line / Quality / Material / Supplier / Load;
- слабейшая компетенция;
- слабейшая производственная зона.

История доступна с другого рабочего места после входа в тот же аккаунт. Данные не завязаны на конкретный браузер.

### Без миграции и нового XP-контура

v6.0.25 использует существующую таблицу `practice_results` и существующую user-scoped схему `practice_storage_session_id`.

Поэтому релиз:

- не добавляет новую таблицу;
- не требует отдельной миграции БД;
- не создаёт новые XP events;
- не меняет spendable/lifetime XP;
- не меняет 20 backend game types;
- не меняет серверный лимит пяти ответов игровых сессий.

### Personal Shift Analytics

В каталоге игр появился блок `PERSONAL SHIFT ANALYTICS · v6.0.25`.

Он показывает:

- количество завершённых смен;
- последний общий результат;
- динамику относительно предыдущего окна;
- средний Production control;
- средний Prioritization;
- средний Production judgement;
- средний Language;
- повторяющуюся точку роста;
- слабую производственную область;
- последние результаты Shift Simulation.

### Персональный следующий шаг

Сервис связывает слабое место с полезной тренировкой:

- Production control → Shift Simulation + Quality Gate;
- Prioritization → Shift Simulation + Shift Incident;
- Production judgement → Quality Gate + Spec or NOK? + Shift Incident;
- Language → Dialogue Duel + Phrase Builder.

Кнопка `Тренировать в новой смене` сразу запускает следующую Shift Simulation.

### Устойчивость при временной потере связи

Если сохранение результата временно невозможно, клиент помещает небольшой pending-result в локальную очередь и повторяет синхронизацию при следующем доступе к истории.

Это fallback, а не основное хранилище: authoritative history остаётся user-scoped PostgreSQL history.

## API

Добавлены два аутентифицированных маршрута:

```text
POST /api/shift-simulations
GET  /api/shift-simulations/history
```

GET возвращает только результаты текущего пользователя.

Маршруты входят в runtime route contract и вставляются до root StaticFiles mount.

## Основные файлы

```text
mgc/routers/shift_analytics.py
mgc_core/shift_analytics_router_bridge.py
static/frontend/shift_analytics_v625.js
static/shift_analytics_v625.css
tests/v625_shift_analytics_test.py
BUILD_INFO_v6.0.25.txt
```

## Совместимость

v6.0.25 является additive release поверх v6.0.24:

- Shift Simulation v6.0.24 остаётся источником Shift Review;
- Production Decision Chains и Dynamic Factory Scenarios не изменены;
- существующие 20 игр не изменены;
- XP/anti-farm не изменены;
- Chinese / English vocabulary parity не изменён;
- Company Pilot и LAN Docker/PostgreSQL/Nginx contracts остаются обязательными CI gates.
