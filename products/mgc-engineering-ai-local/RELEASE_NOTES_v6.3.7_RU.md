# MGC Engineering AI Local v6.3.7
## Engineering Release Handover & Integration Safety

v6.3.7 — технический integration-safety релиз поверх v6.3.6. Новых automotive business-domain модулей релиз не добавляет. Цель — безопасно приблизить released engineering package к контролируемому PLM/PDM/MES handover без автоматического расширения write-поверхности и без machine-control функций.

## Главное
- отдельный outbound handover boundary; существующие read-connectors не превращаются в write API;
- `HANDOVER_WRITE_ENABLED=false` по умолчанию; после обновления production write-back остаётся выключенным;
- `HANDOVER_DRY_RUN_DEFAULT=true`; новый handover job по умолчанию не выполняет внешнюю запись;
- target-code и hostname allowlists по умолчанию пусты;
- controlled `HandoverTarget`, immutable `HandoverJob` и delivery/reconciliation receipts;
- write-target разрешён только для PLM/PDM/MES authority domains;
- write-path/reconcile-path принимаются только как relative gateway paths;
- HTTPS обязателен для production write;
- outbound command фиксирует canonical manifest/payload SHA-256 и idempotency key;
- target для write обязан явно поддерживать idempotency;
- maker-checker: создатель job не может его авторизовать или выполнить; service account не может заменить human checker/executor;
- write execution дополнительно проходит Enterprise Identity Policy v6.3.6;
- bounded retry budget; повтор допускается только тем же immutable idempotency command;
- при `receipt_required=true` отсутствие external receipt считается ошибкой;
- reconciliation требует hash-proof/target-state evidence и fail-closed отклоняет mismatch;
- DB-level trigger запрещает изменение package/target/manifest/request/mode/idempotency/payload identity после создания job;
- Release Manifest остаётся source payload для handover и повторно проверяется перед delivery;
- handover health встроен в Operations Summary, Prometheus и privacy-safe Support Bundle;
- failed/reconciliation-failed или просроченный unreconciled handover переводит Operations в AMBER, но не блокирует PostgreSQL-authoritative Core;
- никакой PLC/robot/conveyor/torque-controller/paint-equipment write path не добавлен;
- admin UI показывает Release Handover posture отдельно от обычной инженерной навигации.

## Runtime defaults
```text
HANDOVER_WRITE_ENABLED=false
HANDOVER_DRY_RUN_DEFAULT=true
HANDOVER_ALLOWED_TARGET_CODES=
HANDOVER_ALLOWED_HOSTS=
HANDOVER_HTTP_TIMEOUT_SECONDS=30
HANDOVER_MAX_ATTEMPTS=3
HANDOVER_RECONCILIATION_MAX_AGE_SECONDS=3600
```

## API
Шесть bounded contexts содержат **224 routes**. Все **181/181** legacy v6.2.0 method/path contracts сохранены. v6.3.7 добавляет controlled target administration, handover job create/read/authorize/execute/reconcile и handover operations summary.

## Schema
Application `6.3.7`, schema `6.3.7`. Добавлены `engineering_handover_targets`, `engineering_handover_jobs`, `engineering_handover_receipts` и DB-level immutable-command trigger. Миграция additive/idempotent и не включает write-back.

## Authority boundary
MGC готовит и доказывает инженерный handover command, но PLM/PDM/MES остаются authority systems. Controlled write возможен только после отдельной корпоративной конфигурации и acceptance. MGC не является PLC/SCADA/robot control system.
