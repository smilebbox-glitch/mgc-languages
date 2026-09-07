# MGC Engineering AI Local v6.3.30 — Production Observability & Automated Incident Evidence

## Основное

v6.3.30 усиливает эксплуатационный слой после v6.3.29: существующие readiness/SLO/queue/integration/workload/HA наблюдения теперь преобразуются в детерминированное privacy-safe evidence для инцидентов. Нового бизнес-домена, тяжёлого интерфейса и новой DB-схемы нет.

### Что добавлено

- canonical `mgc.production-incident-evidence.v1`;
- bounded signal codes для readiness, dependency error-budget, queue age, integration freshness, projection health, workload recovery, brownout, version skew и HA safety;
- детерминированный SHA-256 `signal_fingerprint` без high-cardinality Prometheus labels;
- canonical SHA-256 integrity всего incident-evidence report;
- `GET /api/v1/operations/incident-evidence` для Engineering Admin;
- `POST /api/v1/operations/incident-evidence/reconcile` для управляемой reconciliation;
- `incident-evidence.json` в существующем privacy-safe support bundle;
- `mgc_incident_evidence_signals{severity=...}` с bounded cardinality;
- periodic evidence generation через существующий operational sampling;
- opt-in materialization активных сигналов в существующий `ProductionIncident`;
- дедупликация открытых automated incidents по fingerprint;
- автоматическая severity escalation допускается, automatic resolution — запрещён;
- clear sample никогда не закрывает incident;
- `incident-evidence` добавлен в `mgcctl verify --scope full`.

### Privacy / governance

Incident evidence не содержит raw logs, engineering documents, user queries, credentials, VIN/part history или исходные integration payloads. Каждый report явно фиксирует:

- `automatic_destructive_recovery=false`;
- `automatic_incident_resolution=false`;
- `production_authorized=false`;
- `human_operator_required=true`.

Автоматизация не перезапускает сервисы, не переключает load balancer, не промотирует PostgreSQL и не меняет инженерные source-of-truth данные.

### Материализация инцидентов

По умолчанию:

```text
AUTOMATED_INCIDENT_MATERIALIZATION_ENABLED=false
```

То есть evidence формируется автоматически, но запись новых `ProductionIncident` остаётся opt-in. При включении periodic sampler создаёт/обновляет только активные automated incidents; human resolution остаётся обязательным.

### Совместимость

- Application: **6.3.30**
- DB schema: **6.3.13**
- New DB migration: **нет**
- Rolling/Blue-Green adjacent window: **6.3.29 ↔ 6.3.30**
- 247 bounded-context routes сохранены
- 181/181 legacy v6.2.0 API contracts сохранены

### Верификация

- Backend: **642/642 PASS**, **103/103 test-файла**
- `mgcctl verify --scope full`: **23/23 PASS**
- Production Observability / Incident Evidence preflight: **22/22 PASS**
- Target-Host Assurance: **15/15 PASS**
- Integration Certification: **49/49 PASS**
- Integration Runtime Assurance: **27/27 PASS**

## Ограничение production authorization

v6.3.30 улучшает detection/evidence, но не заменяет target-host probe, production load/SLO certification, CVE/SCA approvals, corporate lock/wheelhouse/image-digest evidence, real PLM/PDM/ERP/MES/QMS certification или human change approval. `production_authorized=false` сохраняется.

## Упаковка

- controlled payload: **1029 файлов**;
- ZIP: **1030 members** с `BUILD_MANIFEST.json`;
- independent manifest verification: missing/extra/size/hash mismatch = **0**;
- cache/test artifacts: **0**;
- ZIP CRC/test: **PASS**.
