# MGC Engineering AI Local v6.3.34 — Pilot Readiness & UX Simplification

Application: **6.3.34**  
Database schema: **6.3.13**  
Migration: **none**

## Цель релиза

v6.3.34 сохраняет pilot-readiness UX, введённый в v6.3.33: инженер сначала видит проект, действия и рабочие объекты, а глубокие Digital Thread / Quality / Launch / Release evidence открывает только при необходимости.

## Основная навигация

Основное меню инженера ограничено пятью рабочими зонами:

1. **Главная** — Action Center и краткий рабочий контекст.
2. **Проекты** — readiness, блокеры и рабочие области проекта.
3. **Детали / BOM** — part/revision/BOM и связанные evidence.
4. **Инструкции** — цех → линия → станция → операция → WI.
5. **Поиск / ИИ** — evidence-first поиск и ответы.

Object 360, документы, проверки и ECR/ECO не удалены. Они открываются контекстно из проекта, Action Center, детали или связанного evidence. IT/HA/resilience/deployment остаются в отдельной административной поверхности.

## Action Center

`project_workspace()` теперь возвращает bounded read-model `action_center`.

Свойства:
- максимум 12 действий на проект;
- стабильная deterministic сортировка: critical → warning/high → medium → info;
- каждый пункт содержит исходный `object_id`, `kind`, `route`, severity и part number при наличии;
- источник — только существующий `project_readiness_evidence`;
- `advisory_only=true`;
- `human_decision_required=true`;
- Action Center ничего не создаёт, не утверждает и не закрывает автоматически.

Это не новый source of truth и не новая workflow-таблица.

## Project Focus Workspace

Первый экран проекта теперь показывает:
- проект и readiness;
- производственную зону;
- Action Center;
- пять рабочих областей проекта;
- краткие counts.

Полный набор engineering gates, Digital Thread, quality/process/launch/supplier/configuration/release panels перенесён под progressive disclosure **«Полная инженерная картина»**.

## Почему это безопасно

- DB schema остаётся 6.3.13;
- API routes остаются 247;
- legacy API contract 181/181 сохранён;
- существующие source-system authority и ACL не меняются;
- readiness остаётся advisory;
- release approval остаётся human-controlled;
- v6.3.32 resilience certification остаётся обязательным deployment baseline;
- rolling/blue-green adjacent window: **6.3.33 ↔ 6.3.34**.

## Что измерять на пилоте

Рекомендуемые KPI после запуска:
- median time-to-find-document;
- median BOM-change impact review time;
- WI preparation/revision time;
- translation review cycle time;
- количество revision conflicts;
- количество traceability gaps, найденных до release;
- доля действий Action Center, закрытых через исходный evidence/workflow;
- субъективная usability оценка инженеров после 1–2 недель.

Текущий pilot-readiness контур намеренно не вводит автоматический «AI productivity score» и не делает выводы об эффективности сотрудника.
