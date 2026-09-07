# MGC Engineering AI Local v6.3.8
## Data Lifecycle, Retention & Compliance Hardening

v6.3.8 продолжает техническое укрепление v6.3.7 и добавляет controlled lifecycle для инженерных данных. Релиз не меняет authority PLM/PDM/MES и не включает внешнюю запись автоматически.

## Главное
- retention policies по типу объекта / проекту / цеху;
- legal hold с exact и scoped matching;
- controlled archive state без удаления source-of-truth;
- 4-eyes purge requests;
- SHA-256 snapshot binding purge authorization;
- append-only hash-chained lifecycle ledger + DB triggers;
- projection-only purge для rebuildable Qdrant/Neo4j Document projections;
- PostgreSQL `document_search_chunks` и local evidence сохраняются при projection purge;
- authoritative purge глобально выключен по умолчанию;
- authoritative purge ограничен unreferenced Document evidence и требует retention policy + elapsed retention + no legal hold;
- released Release Package не является purgeable entity;
- project/area storage quotas, по умолчанию unlimited;
- quota gate применяется к ручной загрузке и connector ingestion;
- evidence lineage API;
- lifecycle metrics в Operations Summary / Prometheus / Support Bundle.

## Runtime defaults
```text
DATA_LIFECYCLE_AUTHORITATIVE_PURGE_ENABLED=false
DATA_LIFECYCLE_PROJECT_QUOTA_MB=0
DATA_LIFECYCLE_AREA_QUOTA_MB=0
DATA_LIFECYCLE_QUOTA_WARNING_PERCENT=80
DATA_LIFECYCLE_RELEASE_RETENTION_DAYS=3650
```

## API
Добавлено 13 Platform Operations routes. Bounded-context surface: 237 routes. Все 181 legacy v6.2.0 method/path contracts сохранены.

## Schema
Application: `6.3.8`
Schema: `6.3.8`

Новые таблицы:
- `engineering_retention_policies`
- `engineering_legal_holds`
- `engineering_data_lifecycle_states`
- `engineering_purge_requests`
- `engineering_lifecycle_events`

Migration additive/idempotent и сама ничего не удаляет.

## Governance boundary
MGC v6.3.8 предоставляет engineering lifecycle controls, а не юридическую систему records management. Реальные corporate retention periods, legal hold procedures, personal-data rules и destruction approvals должны быть утверждены Legal/InfoSec/Data Owner/Records Management.
