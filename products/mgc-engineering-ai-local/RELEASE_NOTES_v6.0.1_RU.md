# MGC Engineering AI Local v6.0.1
## Production Hardening Foundation

v6.0.1 — первый релиз программы промышленного усиления после архитектурного рубежа v6.0. Новые automotive-домены не добавлялись: задача версии — сделать существующую Engineering Intelligence OS безопаснее и эксплуатационно предсказуемее для реального пилота.

## Что изменилось

### 1. Liveness и Readiness разделены

Добавлены:

- `GET /api/v1/health/live` — только проверка жизни API-процесса, без downstream I/O;
- `GET /api/v1/health/ready` — fail-closed проверка обязательных production dependencies;
- старый `GET /api/v1/health` сохранён для обратной совместимости.

Readiness проверяет PostgreSQL, schema marker, evidence storage и по умолчанию Redis/Qdrant. Neo4j/MinIO становятся обязательными только если соответствующие функции включены. Local LLM/VLM намеренно не блокирует deterministic core.

Health response не раскрывает URL, credentials, локальные пути или raw exception text.

### 2. Safe startup schema bootstrap

Startup schema work теперь сериализуется PostgreSQL advisory lock с bounded timeout. Добавлен operational schema marker `6.0.1`, который входит в readiness.

Это снижает риск гонки миграций при запуске нескольких API replicas.

### 3. Исправлен healthcheck Celery worker

Ранее worker наследовал HTTP healthcheck API image и мог считаться unhealthy, потому что Celery не слушает порт API. В v6.0.1 worker использует отдельный Celery ping именно своего node.

### 4. Operational observability

Добавлены Prometheus metrics:

- `mgc_operational_readiness`;
- `mgc_dependency_up`;
- `mgc_dependency_check_latency_ms`.

Добавлен `X-Request-ID` и privacy-minimized structured HTTP logging. Логи используют route template и не пишут query string/body/VIN/part number из фактического URL или identity.

### 5. Core backup

Добавлен `make backup` / `scripts/backup_core.sh`.

Checksum-verified backup set включает:

- PostgreSQL custom dump;
- evidence storage archive;
- Qdrant collection snapshot;
- `BACKUP_MANIFEST.json`;
- `SHA256SUMS`.

`.env`, secrets, model weights и container images намеренно не копируются в application backup.

### 6. Guarded restore

Добавлен `scripts/restore_core.sh`.

Restore требует явного `MGC_RESTORE_CONFIRM=RESTORE`, проверяет SHA-256, по умолчанию создаёт pre-restore safety backup, восстанавливает PostgreSQL/evidence/Qdrant и не возвращает user traffic до успешного `/health/ready`.

### 7. DR / Operations runbooks

Добавлены:

- `docs/PRODUCTION_OPERATIONS.md`;
- `docs/BACKUP_RESTORE_DR.md`;
- `scripts/dr_preflight.py`;
- Make targets `health`, `backup`, `restore`, `dr-preflight`.

### 8. Plain `docker compose build`

`env_file` переведён в optional build-safe mapping. Поэтому сама стадия build не требует наличия production `.env`. Перед production start/acceptance корректные OIDC/secrets по-прежнему обязательны.

## Что не заявляется

v6.0.1 не является доказательством enterprise-wide production readiness. В этой упаковочной среде не выполнялись:

- реальный Docker image build;
- Dockle layer scan;
- live backup/restore drill;
- PostgreSQL HA/PITR validation;
- enterprise load benchmark;
- penetration test.

Эти gates должны выполняться на approved corporate runtime/build host и в пилотной инфраструктуре.

## Следующий шаг программы hardening

После v6.0.1 — Integration Hardening + Data Confidence: реальные adapter contracts для PLM/PDM/ERP/MES/QMS, idempotent sync, quarantine/dead-letter handling, source freshness и confidence/provenance для импортированных инженерных данных.
