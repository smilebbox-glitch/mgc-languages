# MGC Engineering AI Local v6.0.8 — Observability, Reliability & Production Support

## Назначение релиза

v6.0.8 — восьмой шаг production-hardening после Engineering Intelligence OS. Релиз не добавляет новый automotive-домен и не меняет ownership PLM/PDM/ERP/MES/QMS. Цель — дать корпоративному IT/SRE эксплуатационный слой: SLI/SLO, error budgets, bounded-cardinality metrics, queue/integration lag, incident evidence, privacy-safe support bundle и runbook-driven troubleshooting.

## Основные изменения

### SLI / SLO / Error Budget
- Добавлена локальная история readiness samples по bounded component names.
- Для required dependencies рассчитываются target, observed availability, bad events, allowed bad events, budget consumed и budget remaining.
- По умолчанию target dependency availability = 99.5%.
- История health samples имеет retention 30 дней по умолчанию.
- Multi-replica API latency/availability time-series остаются зоной Prometheus/OTel; MGC не выдаёт локальные samples за полноценную observability backend.

### Application metrics
- `mgc_http_requests_total` — method + route template + status class.
- `mgc_http_request_duration_seconds` — method + route template.
- `mgc_queue_depth` и `mgc_queue_oldest_age_seconds`.
- `mgc_integration_lag_seconds`.
- `mgc_open_incidents`.
- `mgc_slo_error_budget_remaining_ratio`.
- Prometheus labels не используют user/VIN/part/document/query identifiers.

### Queue / Integration lag
- Отображается Redis/Celery queue depth, когда Redis доступен.
- Oldest queued/running `ComputeJob` age вычисляется из authoritative job records.
- Для ExternalSystem рассчитывается lag относительно last sync и freshness SLA.
- Integration freshness target по умолчанию = 95%.

### Production incident evidence
Добавлена отдельная operator-domain сущность `ProductionIncident`:
- severity: low / medium / high / critical;
- status: open / mitigating / monitoring / resolved;
- component, summary, impact, evidence, resolution summary;
- resolution требует явного resolution summary.

Operational incident не заменяет QMS defect/8D и не используется как engineering root-cause record.

### Privacy-safe support bundle
Engineering Admin может экспортировать support bundle через `/api/v1/operations/support-bundle`.

Внутри только:
- privacy-safe readiness snapshot;
- operational summary;
- security posture;
- manifest с SHA-256.

Не включаются:
- raw application logs;
- document content;
- raw AI queries;
- user/IP history;
- VIN/part browsing history;
- integration secrets;
- raw incident evidence payload.

### Hardened Celery Beat
- Base и air-gap Compose stacks теперь включают hardened Beat scheduler.
- Periodic health sampling активируется `OPERATIONAL_SAMPLING_ENABLED=true`.
- В enterprise overlay Beat использует runtime-only PostgreSQL identity и `AUTO_MIGRATE_SCHEMA=false`.
- DDL остаётся только у one-shot schema migration service.

### Admin API
- `GET /api/v1/operations/summary`
- `GET /api/v1/operations/slo`
- `POST /api/v1/operations/health-samples`
- `GET /api/v1/operations/incidents`
- `POST /api/v1/operations/incidents`
- `PATCH /api/v1/operations/incidents/{incident_id}`
- `GET /api/v1/operations/support-bundle`

Все human-facing operations endpoints проходят обычный `get_identity` authorization gate и требуют Engineering Admin для operational detail/mutation/export.

## UI
В IT/admin workspace добавлена компактная карточка `Production Support · v6.0.8`:
- overall state;
- dependency SLO;
- remaining error budget;
- queue age;
- integration freshness;
- open/critical incidents.

## Governance
MGC не выполняет автоматический restart/failover/destructive repair, не закрывает incidents автоматически и не авторизует production deployment. Красный SLO/incident signal — основание для human operator response по утверждённому runbook.

## Runtime gates, которые остаются внешними
В packaging environment не выполнялись и не заявляются как PASS:
- реальный Docker image build/runtime acceptance;
- Dockle image-layer scan;
- Trivy/Grype resolved-image CVE scan;
- production npm/wheelhouse resolved dependency scan;
- реальные AD/OIDC/PKI/mTLS negative tests;
- real backup→restore drill;
- target-host Prometheus/OTel retention/alert routing validation;
- Pilot/Enterprise live load test.
