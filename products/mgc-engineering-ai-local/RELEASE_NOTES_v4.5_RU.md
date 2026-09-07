# MGC Engineering AI Local v4.5.0 — Release Notes

## Supplier & Localization Engineering

Добавлен компактный автомобильный supplier/localization layer внутри Project Workspace.

### Новое

- локализуемая деталь + supplier identity;
- Localization KPI отдельно от Supplier Readiness;
- RFQ / technical package / nomination / tooling / capacity статусы;
- автоматическое использование PPAP и Run@Rate;
- incoming-quality records с defect-rate calculation;
- блокировка high/critical supplier issue без 8D;
- Localization Evidence Pack;
- Supplier gate в Project Readiness только после настройки модуля;
- одна сворачиваемая UI-карточка без нового пункта основного меню.

### Governance

- `localization_percent` является справочным KPI и не выдаёт approval;
- supplier readiness носит advisory характер;
- финальное одобрение поставщика остаётся за корпоративным процессом;
- Project / Manufacturing Area / Document ACL продолжают действовать.

### Verification

- backend tests: 110/110 PASS;
- human-facing API identity gate: 105/105 PASS;
- Dockerfile static security: 32/32 PASS;
- Compose/runtime security: 82/82 PASS;
- plain `docker compose build` preflight: PASS;
- TSX transpile: PASS.

Реальный Docker build и Dockle layer scan должны выполняться на корпоративном Docker build-host.
