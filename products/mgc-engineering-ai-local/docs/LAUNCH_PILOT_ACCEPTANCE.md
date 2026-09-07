# Pilot Acceptance — Launch & Plant Readiness v4.3

## Рекомендуемый пилот

Использовать один автомобильный проект и 2–3 производственные зоны, например Сварка + Сборка + Логистика.

## Сценарий 1 — Tooling / Equipment

1. Создать Launch Check `ASM-TOOL-01` в зоне Сборка.
2. Связать его с линией.
3. Оставить статус `planned` — карточка должна показать gap.
4. Перевести в `ready` — gap должен исчезнуть.
5. Создать в Process Digital Thread средство измерения с просроченной calibration date — tooling/equipment gate должен ухудшиться независимо от ручного Launch Check.

## Сценарий 2 — Run@Rate

1. Создать `RAR-01` с target 60 шт./ч.
2. Внести actual 52 шт./ч и status `passed`.
3. Система обязана показать critical capacity mismatch.
4. Исправить actual до 62 шт./ч и приложить evidence — blocker должен исчезнуть после обновления.

## Сценарий 3 — Supplier / PPAP

1. Создать supplier readiness check.
2. Добавить PPAP со статусом `approved` — supplier/PPAP gate должен учитывать его автоматически.
3. Изменить PPAP на `rejected` — Launch Readiness должен показать critical blocker.

## Сценарий 4 — Pilot / DV / PV

Создать Pilot Build, DV и PV. Проверить, что незавершённые trials влияют только на соответствующий configured gate и не создают скрытого автоматического SOP approval.

## Сценарий 5 — 8D / ECR

Открытый high/critical 8D или high-risk ECR/ECO должен появляться в risk-closure launch context без повторного ручного ввода.

## Сценарий 6 — ACL

Инженер сборки открывает `Все зоны`. Данные Launch Readiness закрытой зоны Окраска не должны присутствовать в checks, trials, gaps или агрегированной readiness.

## Acceptance gates

- engineer-only SSO: PASS;
- manufacturing-area ACL: PASS;
- document evidence ACL: PASS;
- Run@Rate target-vs-actual validation: PASS;
- no automatic SOP release: PASS;
- no MES/SCADA write capability: PASS;
- `docker compose build`: PASS on corporate build host;
- Dockle: PASS on built images according to corporate policy.
