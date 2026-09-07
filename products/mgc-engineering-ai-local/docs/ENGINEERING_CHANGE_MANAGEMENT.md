# Engineering Change Management — v3.8.0

## Цель

Свести изменение конструкции в один аудируемый маршрут, связанный с существующими CAD, drawing, BOM, Design Review и document history.

```text
ECR Draft
   ↓
Impact Analysis
   ↓
Technical Review (другой инженер)
   ↓
Final Approval (Engineering Admin)
   ↓
ECO Released
   ↓
Implementation
   ↓
Verification
   ↓
Implemented
```

## Fail-closed правила

- Автор ECR не может согласовать собственное изменение.
- Final Approval требует предыдущего approved Technical Review.
- Для High/Critical risk требуется approved Design Review.
- Impact analysis фиксирует `document_id + SHA-256`. Если исходная доказательная база изменилась, ECO не выпускается до повторного impact analysis.
- Доступ к API изменения наследует engineer-only SSO/OIDC protection.

## Audit trail

`ChangeEvent` — append-only события. Каждый event содержит `previous_hash` и `event_hash`. `ChangeEventState` хранит отдельный `head_hash` и `event_count`, поэтому проверка обнаруживает изменение, удаление события в середине и удаление последнего события.

Ключевые события:

- ECR_CREATED
- IMPACT_ANALYZED
- IMPACT_STALE
- SUBMITTED_FOR_APPROVAL
- CHANGE_DECISION
- IMPLEMENTATION_STARTED
- IMPLEMENTED

Ключевые change-события также отражаются в `DocumentActivity` затронутых документов.

## API

- `GET /api/v1/changes`
- `POST /api/v1/changes`
- `GET /api/v1/changes/{id}`
- `POST /api/v1/changes/{id}/impact`
- `POST /api/v1/changes/{id}/submit`
- `POST /api/v1/changes/{id}/decision`
- `POST /api/v1/changes/{id}/implementation`
- `POST /api/v1/changes/{id}/complete`

## Роли

**Author** — создаёт ECR и отправляет его на review.

**Technical reviewer** — любой другой инженер с доступом к детали.

**Final approver** — Engineering Admin.

**Implementation owner** — инженер, начавший внедрение; он либо Engineering Admin может закрыть изменение после verification.
