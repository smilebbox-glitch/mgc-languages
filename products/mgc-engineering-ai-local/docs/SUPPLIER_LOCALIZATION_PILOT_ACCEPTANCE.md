# Pilot Acceptance — Supplier & Localization Engineering v4.5

Пилот лучше проводить на одной локализуемой детали и одном реальном/тестовом поставщике.

## Роли

- R&D / Product Engineer;
- Supplier Quality Engineer;
- Purchasing / localization owner;
- Engineering Admin.

## Сценарий

1. Открыть автомобильный проект и выбрать зону `Компоненты` или другую применимую зону.
2. Добавить локализуемую деталь и поставщика.
3. Установить `Localization KPI = 100%`, оставив technical package `missing`.
   - ожидается: Supplier Readiness не становится 100%; появляется gap технического пакета.
4. Перевести RFQ в `complete`, nomination в `approved`, tooling в `ready`.
5. Добавить PPAP в существующем Quality-модуле со статусом `approved`.
6. Добавить Run@Rate в Launch-модуле: target 60 шт/ч, actual 64 шт/ч, status `passed`.
   - ожидается: PPAP и Capacity gate = 100%.
7. Создать Incoming Quality: inspected 100, defects 5, limit 1%, severity `critical`.
   - ожидается: critical blocker по превышению defect rate.
8. Убедиться, что critical/high IQ без 8D создаёт отдельный blocker.
9. Создать 8D и связать его с IQ record.
   - ожидается: `8D missing` исчезает, но открытый 8D остаётся в risk closure до закрытия.
10. Сформировать Localization Evidence Pack.
    - проверить snapshot supplier/readiness/PPAP/capacity/IQ.

## ACL negative test

1. Создать скрытую Paint-деталь с document ACL `paint-secret`.
2. Дать пользователю доступ только к Components.
3. Открыть `Все зоны`.
4. Ожидается: Paint localization item, incoming quality и evidence отсутствуют в выдаче.

## Приёмочные критерии

- Localization KPI не используется как automatic approval;
- PPAP/Run@Rate повторно используются без дублей;
- defect-rate limit проверяется по фактическим числам;
- high/critical supplier issue без 8D блокируется;
- Evidence Pack содержит snapshot, а не живую ссылку на меняющийся score;
- все human API требуют engineer identity;
- Project/Area/Document ACL не обходятся;
- старые проекты без localization data не меняют readiness.
