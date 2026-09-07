# MGC Engineering AI Local v6.3.19
## Database & Evidence Storage HA

v6.3.19 продолжает v6.3.18 и добавляет fail-closed защиту для двух оставшихся authoritative single points of failure: PostgreSQL и evidence storage. Схема БД не меняется: application **6.3.19**, schema **6.3.13**.

## Главное

- PostgreSQL HA probe проверяет `pg_is_in_recovery()` и `transaction_read_only`;
- корпоративный deployment может закрепить точный PostgreSQL `system_identifier`;
- `mgc_schema_state=6.3.13` теперь входит в authoritative DB fence и mismatch/missing marker блокирует запись;
- mutating HTTP API получает общий authoritative write fence;
- Celery/maintenance/non-HTTP writes дополнительно fenced на `before_flush`, bulk ORM UPDATE/DELETE и финальном `before_commit`;
- evidence storage получает target-local cluster/generation marker;
- symlinked marker/path-компоненты блокируются fail-closed, marker update использует atomic replace + `fsync`;
- запись разрешается только при `state=active`, корректной generation и совпадающем cluster id;
- evidence generation может быть привязана к PostgreSQL system identifier;
- `.mgc-ha` исключён из engineering evidence fingerprint и backup archive;
- guarded evidence promotion требует recovery point, expected generation и явный `PROMOTE_EVIDENCE`;
- recovery point связывает logical PostgreSQL SHA-256, evidence tree SHA-256, WAL LSN, cluster identity и consistency epoch;
- readiness блокируется, если authoritative ownership не доказан;
- добавлен `GET /api/v1/operations/authoritative-ha`;
- Prometheus и Support Bundle получают authoritative HA diagnostics;
- обычный developer Compose не усложняется;
- `docker-compose.authoritative-ha.yml` предназначен только для deployment с внешним PostgreSQL HA-manager и approved shared/replicated evidence storage;
- MGC не выполняет PostgreSQL promotion/ST​ONITH и не заявляет storage replication как собственную функцию.

## Команды

```bash
make authoritative-ha-preflight
make authoritative-ha-check
make authoritative-recovery-point OUTPUT=/secure/path/recovery-point.json
make authoritative-ha-up
```

Управление target-local evidence marker:

```bash
python scripts/evidence_ha_marker.py --storage /data/storage init ...
python scripts/evidence_ha_marker.py --storage /data/storage demote --confirm DEMOTE_EVIDENCE
python scripts/evidence_ha_marker.py --storage /data/storage promote ... --confirm PROMOTE_EVIDENCE
```

## Production boundary

Production HA требует внешнего PostgreSQL quorum/failover/fencing, реальной репликации или shared storage, независимого entry load balancer и target-host failover drill. `production_authorized=false` сохраняется во всех автоматически генерируемых recovery/promotion evidence.
