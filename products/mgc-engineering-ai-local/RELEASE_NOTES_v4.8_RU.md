# MGC Engineering AI Local v4.8.0

## Vehicle Variant & Configuration Management

Добавлено:

- VehicleVariant: рынок, Model Year, кузов, двигатель, трансмиссия, комплектация и произвольные атрибуты;
- явная applicability для parts/documents/architecture nodes/interfaces/requirements/ECR-ECO;
- безопасная семантика `unknown != included`;
- приоритет explicit part exclusion над interface-derived inclusion;
- part-level configuration impact;
- ECR/ECO variant impact;
- Project Readiness configuration gate только после включения модуля;
- fail-closed filtering по evidence/area/document ACL;
- компактная UI-карточка без расширения основной навигации;
- additive/idempotent v4.8 schema upgrade.

Модуль advisory-only и не заменяет PLM/PDM configuration authority.
