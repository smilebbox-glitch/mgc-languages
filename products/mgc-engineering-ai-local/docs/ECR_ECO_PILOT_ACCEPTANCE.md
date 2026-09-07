# ECR/ECO Pilot Acceptance — v3.8.0

Используйте три разные корпоративные учётные записи:

- `Engineer A` — автор ECR;
- `Engineer B` — technical reviewer;
- `Engineering Admin C` — final approver.

## Happy path

1. Engineer A открывает **Изменения → Создать ECR**.
2. Выбирает существующую деталь и две существующие ревизии.
3. Запускает **Рассчитать влияние**.
4. Проверяет risk score, затронутые сборки/документы и Design Review gate.
5. Отправляет ECR на согласование.
6. Проверить, что Engineer A не может сделать technical approval.
7. Engineer B выполняет technical approval.
8. Проверить, что Engineer B не может выполнить final approval даже при наличии admin-роли.
9. Engineering Admin C выпускает ECO.
10. Исполнитель фиксирует implementation plan и verification plan.
11. После внедрения вводит verification result и закрывает ECO.
12. Проверить Change timeline и историю затронутого чертежа.

## Stale impact test

После шага 7, но до final approval:

- заменить/переиндексировать один из затронутых drawing/BOM/CAD документов **или** добавить новую BOM-связь, влияющую на сборку;
- попытаться выпустить ECO.

Ожидаемый результат: final approval блокируется, статус возвращается в `impact_review`, появляется событие `IMPACT_STALE`. После повторного impact analysis процесс можно отправить на approval заново.

## High-risk gate

Для изменения с `risk_level=high/critical`:

- без approved Design Review ECO не выпускается;
- после approved Design Review final approval разрешается при неизменной impact evidence.

## Security acceptance

- пользователь вне engineering groups не видит UI/API;
- Engineer A/B видят только изменения по доступным им инженерным данным;
- final approval доступен только Engineering Admin;
- `/api/v1/changes*` не должен работать без `get_identity`;
- история изменения должна возвращать `history_integrity_valid=true`.
