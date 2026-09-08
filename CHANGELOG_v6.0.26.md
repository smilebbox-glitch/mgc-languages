# v6.0.26 — Manager / Team Analytics + Top-10 Leaderboard

## Цель

Завершить управленческий контур пилота без превращения учебной платформы в HR-рейтинг и добавить понятную соревновательную механику после коротких игровых заданий.

## Manager / Team Analytics

В разделе руководителя появляется агрегированный блок `TEAM ANALYTICS · v6.0.26`.

Для manager роль жёстко ограничена собственным `department`. Попытка запросить другое подразделение отклоняется сервером. Admin может использовать агрегированный просмотр шире.

Показываются только командные учебные сигналы:

- число сотрудников в scope;
- сколько сотрудников прошли Shift Simulation;
- количество завершённых смен;
- participation rate;
- средние Production control / Prioritization / Production judgement / Language;
- factory health: Line / Quality / Material / Supplier / Team load control;
- наиболее слабая командная компетенция;
- наиболее слабая производственная зона;
- рекомендуемый следующий тип тренировки;
- соотношение китайских и английских смен.

Командные средние балансируются по сотрудникам, чтобы один активный пользователь с большим количеством попыток не определял всю картину подразделения.

Экран явно помечен как учебная аналитика и не является HR-оценкой профессиональной пригодности.

## Top-10 Leaderboard

После завершённого серверного игрового задания отображается Top-10 своего подразделения.

Правило сортировки:

1. выше score;
2. при одинаковом score — меньше duration;
3. один сотрудник занимает только одно место — учитывается его лучшая попытка.

Показываются:

- место 1–10;
- display name;
- score / total;
- время прохождения;
- отдельная подсветка текущего пользователя;
- фактическое место текущего пользователя, даже если оно ниже Top-10.

Leaderboard scope — подразделение текущего пользователя. Username, email и другие внутренние идентификаторы в рейтинг не выводятся.

## Shift timing foundation

Shift Simulation persistence получил опциональный `duration_ms` внутри существующего компактного `PracticeResult.topic` payload. Новая таблица и миграция БД не требуются. Исторические v6.0.25 записи без времени остаются валидными и не участвуют в timed shift leaderboard до появления timed результатов.

## API

Добавлены read-only маршруты:

```text
GET /api/manager/shift-analytics
GET /api/leaderboards/games/{game_type}
GET /api/leaderboards/shifts
```

Они входят в runtime route contract и загружаются до root StaticFiles mount.

## XP / anti-farm

v6.0.26 не добавляет XP events, не меняет spendable/lifetime XP и не меняет существующий anti-farm. Рейтинг использует уже сохранённый сервером score и server-side timestamps.

## Основные файлы

```text
mgc/routers/team_analytics.py
mgc_core/team_analytics_router_bridge.py
static/frontend/team_leaderboard_v626.js
static/team_leaderboard_v626.css
tests/v626_team_leaderboard_test.py
BUILD_INFO_v6.0.26.txt
```
