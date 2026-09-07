# MGC Engineering AI Local v6.3.10
## Cache, Read Models & Object 360 Performance

v6.3.10 — технический performance-релиз поверх v6.3.9. Новых automotive business-domain функций не добавляет. Цель — ускорить тяжёлые read-surfaces без создания нового source of truth.

## Главное

- PostgreSQL-backed `EngineeringReadModel` для rebuildable derived aggregates;
- первый read model: Work Instruction / station coverage по Project + Manufacturing Area;
- optional Redis acceleration для Object 360, Project Workspace и WI Workspace;
- cache key включает ACL fingerprint; разные visibility scopes не делят full-payload cache;
- private `ETag` + `If-None-Match` для Object 360 / Project Workspace / WI Workspace;
- transactional `read_model_invalidate` events через существующий Projection Outbox;
- pending invalidation заставляет read-path обходить cache до доставки события;
- Redis outage деградирует только производительность, а не correctness;
- admin status/rebuild API для read models;
- read-model persistence не хранит WI/document text — только безопасные aggregates + hashes;
- все 181 v6.2.0 legacy method/path contracts сохранены.

## Runtime defaults

- `READ_MODEL_ENABLED=true`
- `READ_MODEL_CACHE_ENABLED=true`
- `READ_MODEL_CACHE_TTL_SECONDS=60`
- `READ_MODEL_PENDING_INVALIDATION_BYPASS=true`
- `OBJECT360_CACHE_TTL_SECONDS=30`

Redis остаётся transient acceleration/queue dependency и не становится engineering source of truth.

## Version

- Application: `6.3.10`
- Schema: `6.3.10`
- Bounded-context routes: `241`
- Full backend inventory: `414 tests`
