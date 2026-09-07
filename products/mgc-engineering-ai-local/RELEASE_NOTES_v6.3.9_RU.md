# MGC Engineering AI Local v6.3.9
## Database Performance & Scale Hardening

v6.3.9 — технический релиз производительности поверх v6.3.8. Новых automotive business-domain функций не добавляет. Цель — сделать текущий Engineering Digital Thread предсказуемее при росте количества инженеров и объёма BOM/WI/audit/projection данных.

## Главное
- bounded SQLAlchemy pool для PostgreSQL;
- privacy-safe slow-query telemetry без SQL text/bind values;
- request-level SQL statement/time budget и N+1 heuristic;
- hard query-budget enforcement выключен по умолчанию;
- additive composite indexes для ключевых engineering/operations access paths;
- отдельный keyset/cursor endpoint для больших audit trails без изменения legacy `/audit`;
- bounded bulk INSERT для BOM CSV и PostgreSQL authoritative search chunks;
- reference load profiles `pilot_15`, `pilot_30`, `enterprise_100`;
- admin `GET /api/v1/operations/performance`;
- DB performance posture включён в Operations Summary и Support Bundle;
- existing v6.2–v6.3.8 governance, WI/BOM translation, layouts, outbox, approvals, identity, handover и lifecycle сохранены.

## Безопасные defaults
`DB_QUERY_BUDGET_ENFORCEMENT_ENABLED=false`. Релиз измеряет и сигнализирует, но не начинает автоматически прерывать тяжёлые инженерные запросы. Включение hard budget должно быть основано на target-host benchmark.

## Scale profiles
Профили 15/30/100 инженеров являются reference envelope, а не обещанием throughput. Для `enterprise_100` обязательны target-host PostgreSQL/Qdrant/Redis benchmarks, representative BOM/WI/Object 360 data и DBA review.

## Версии
- Application: `6.3.9`
- Schema: `6.3.9`
- Migration: additive/idempotent indexes only; engineering rows не переписываются.

## API
- 239 routes в шести bounded contexts;
- 181/181 legacy v6.2.0 method/path сохранены;
- новые additive endpoints: `/operations/performance`, `/audit/cursor`.
