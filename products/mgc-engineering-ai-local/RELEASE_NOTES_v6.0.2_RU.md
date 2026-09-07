# MGC Engineering AI Local v6.0.2 — Integration Hardening & Data Confidence

## Цель релиза

v6.0.2 — второй шаг Production Hardening после v6.0.1. Релиз не добавляет новый automotive-домен. Он укрепляет интеграционный слой PLM/PDM/ERP/MES/QMS/CAD/Files и делает качество внешних инженерных данных наблюдаемым и аудируемым.

## Единый integration contract

Каждый источник получает контролируемый контракт с:

- source domain и stable external identity;
- обязательными полями;
- contract version;
- разрешёнными object kinds;
- source revision/checksum/timestamp;
- expected freshness SLA;
- допустимым clock skew.

MGC остаётся consumer/intelligence layer и не становится source of truth для PLM, ERP, MES или QMS.

## Data Confidence

Для принятого evidence рассчитывается прозрачный breakdown, а не непрозрачный AI-score:

- schema validity — 35%;
- completeness — 25%;
- freshness — 20%;
- source identity — 10%;
- provenance — 10%.

Итоговый уровень: HIGH / MEDIUM / LOW. LOW сам по себе не удаляет и не блокирует валидный engineering evidence. Contract-invalid payload обрабатывается отдельно через quarantine.

Freshness пересчитывается относительно текущего времени, поэтому вчерашний HIGH не остаётся HIGH навсегда без нового source evidence. Если SLA freshness настроен, но source timestamp отсутствует, итоговый confidence не может быть HIGH.

## Idempotent ingestion ledger

Добавлен `integration_ingest_events` ledger. Для каждого события сохраняются:

- integration/source identity;
- idempotency key;
- source revision/fingerprint;
- payload SHA-256;
- source timestamp;
- validation result;
- quality breakdown;
- accepted/quarantined/failed/replayed status;
- attempt history.

Если источник не предоставляет checksum/revision/source timestamp, MGC сначала получает payload и использует SHA-256 содержимого как сильную idempotency identity. Это предотвращает пропуск реального изменения при неизменившихся слабых metadata.

## Quarantine / DLQ / replay

Payload, нарушающий integration contract, не индексируется как controlled engineering evidence. Он сохраняется локально как immutable quarantined evidence с checksum-identifiable payload и записью в ingest ledger.

Автоматический polling не зацикливается на одном и том же quarantined event. После исправления mapping/contract Engineering Admin может выполнить явный replay; replay снова проходит текущую contract validation и не обходит правила безопасности.

Физические quarantine paths и connector secrets не возвращаются пользовательским API.

## Document mode и record mode

Один integration fabric теперь поддерживает два режима:

1. document/content mode — для PLM/PDM/file-oriented систем с download endpoint;
2. `record_mode` — для ERP/MES/QMS REST records, где JSON source record сериализуется в immutable JSON evidence без обязательного content-download endpoint.

Добавлены vendor-neutral REST connector types для MES и QMS наряду с существующими PLM/PDM/ERP/engineering adapters.

## Sync concurrency

Для PostgreSQL добавлен per-source advisory lock с bounded timeout. Одна интеграция не может одновременно синхронизироваться двумя worker/API replicas, что защищает checkpoint и idempotency ledger от гонок при горизонтальном масштабировании.

## Observability

Integration API и admin UI показывают health отдельно от data quality. Добавлены/расширены:

- current confidence level/score;
- freshness SLA и фактический age;
- quarantine count;
- integration run quality;
- Prometheus `mgc_integration_data_confidence`;
- Prometheus `mgc_integration_quarantine_events`.

Transport `health=ok` больше не трактуется как доказательство актуальности или полноты инженерных данных.

## API

Добавлены/усилены admin endpoints:

- `GET /api/v1/integrations/{system_id}/quality`;
- `GET /api/v1/integrations/{system_id}/quarantine`;
- `POST /api/v1/integrations/{system_id}/quarantine/{event_id}/replay`.

Все human-facing integration endpoints проходят обычный `get_identity`; replay требует административной границы. HMAC webhook остаётся явным machine-to-machine exception.

## UI

В IT/System разделе integration card теперь показывает:

- source domain / connector type;
- transport health;
- sync status;
- Data Confidence;
- confidence percentage;
- outstanding quarantine count.

Инженерный основной интерфейс не перегружен новым глобальным разделом.

## Governance

- MGC не исправляет PLM/ERP/MES/QMS source data автоматически.
- LOW confidence — сигнал качества данных, не автоматический engineering rejection.
- Stale-but-valid evidence остаётся видимым с пониженным confidence.
- Contract-invalid evidence не становится controlled engineering evidence до успешного replay/resync.
- Connector secrets и внутренние filesystem paths не раскрываются API.

