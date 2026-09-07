# Supplier & Localization Engineering — v4.5

## Назначение

Модуль связывает локализацию автомобильной детали с фактической инженерной готовностью поставщика. Он не считает процент локализации доказательством готовности и не заменяет решение R&D / SQE / Purchasing / Quality.

Цифровая цепочка:

```text
Проект / производственная зона
        ↓
Локализуемая деталь
        ↓
Supplier / RFQ / технический пакет / nomination
        ↓
Tooling / equipment
        ↓
Capacity / Run@Rate
        ↓
PPAP
        ↓
Incoming Quality
        ↓
Supplier 8D / ECR-ECO
        ↓
Supplier Readiness + Evidence Pack
```

## Два разных показателя

### Localization KPI
Информационный процент локализации. Может использоваться для внутренних целей проекта, но не участвует напрямую как доказательство готовности поставщика.

### Supplier Readiness
Рекомендательная инженерная оценка по восьми gate:

- Technical package — 15%;
- RFQ — 10%;
- Nomination — 10%;
- Tooling — 15%;
- Capacity / Run@Rate — 15%;
- PPAP — 20%;
- Incoming Quality — 10%;
- Risk closure / 8D — 5%.

Если модуль локализации для проекта ещё не настроен, Supplier gate не меняет старый Project Readiness.

## Автоматическое повторное использование evidence

Сервис использует уже существующие данные проекта:

- `PPAPSubmission` → PPAP gate;
- `LaunchTrial(run_at_rate)` → capacity gate;
- `LaunchReadinessItem(tooling/equipment)` → tooling evidence;
- `Problem8D` → risk closure;
- документы проекта → technical package evidence;
- ACL производственной зоны и документа остаются обязательными.

Одни и те же факты не нужно повторно вводить в Supplier-модуль.

## Incoming Quality

Запись входного контроля хранит:

- поставщика;
- деталь / ревизию;
- lot/reference;
- проверенное, отклонённое и дефектное количество;
- severity;
- допустимый defect-rate limit;
- evidence;
- связь с 8D.

Если фактическая дефектность выше заданного лимита, сервис поднимает critical supplier blocker независимо от ручного статуса локализации.

High/Critical supplier problem без связанного 8D также является critical gap.

## Localization Evidence Pack

Для каждой локализуемой детали можно сформировать immutable snapshot:

- supplier identity;
- localization status;
- Supplier Readiness на момент формирования;
- PPAP snapshot;
- Run@Rate/capacity snapshot;
- tooling checks;
- incoming-quality records;
- открытые риски;
- список видимых evidence documents.

Evidence Pack нужен для аудита и инженерного review; он не является автоматическим одобрением поставщика.

## Безопасность

Действует существующая цепочка:

```text
Engineer SSO
  → Project ACL
  → Manufacturing Area ACL
  → Document ACL
  → Supplier / Localization data
```

Режим `Все зоны` не расширяет ACL. Скрытый документ или закрытая производственная зона не становятся видимыми через Supplier Workspace.

## Интерфейс

Основное меню не расширено. В Project Workspace добавлена одна сворачиваемая карточка **«Поставщики и локализация»**.

В закрытом состоянии видны только:

- Supplier Readiness;
- Localization KPI;
- PPAP gate;
- Incoming Quality gate;
- до трёх основных gaps.

Подробные RFQ/tooling/capacity/IQ формы открываются только по кнопке.
