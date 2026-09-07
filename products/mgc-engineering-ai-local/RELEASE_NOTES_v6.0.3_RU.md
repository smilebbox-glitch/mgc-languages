# MGC Engineering AI Local v6.0.3 — Real Integration Pilot & Data Reconciliation

v6.0.3 продолжает production-hardening после v6.0.2. Релиз не добавляет новый automotive-домен и не становится системой-источником. Его задача — доказуемо сверять реальные данные PLM/PDM, ERP, MES и QMS перед контролируемым корпоративным пилотом.

## Что добавлено

### Canonical Entity Mapping Registry

Добавлен `IntegrationEntityMapping` для подтверждённых соответствий внешних идентификаторов к каноническим сущностям MGC:

- Part;
- VIN;
- Supplier;
- BOM position;
- defect/linkage key.

Точные канонические идентификаторы не требуют mapping-записи. Alias mapping создаётся/подтверждается человеком. Mapping хранит fingerprint исходного ExternalObject и становится `STALE`, если источник изменился; stale mapping не применяется для получения зелёного reconciliation result.

Один внешний BOM row может иметь отдельные mapping keys для parent part, child part и supplier. Mapping применяется только к копии данных для reconciliation и никогда не переписывает исходный PLM/ERP/MES/QMS payload.

### PLM EBOM ↔ ERP MBOM reconciliation

Добавлена read-only детерминированная сверка:

- missing / extra positions;
- replacement;
- revision mismatch;
- quantity / unit mismatch;
- supplier mismatch;
- moved position / field-level drift, где это поддерживается существующим BOM comparator.

PLM/ERP остаются authoritative systems. MGC не выбирает победителя автоматически при конфликте.

### Released configuration ↔ MES genealogy

Для VIN/part/revision внешняя MES genealogy сопоставляется с доказуемой released configuration:

- immutable Release Baseline manufacturing BOM / BOM;
- Configuration Effectivity fallback, если это допустимо по имеющимся данным.

Результат: `MATCH`, `MISMATCH` или `REVIEW_REQUIRED`. Никакой записи обратно в MES нет.

### QMS ↔ Part / VIN / Supplier linkage

QMS defect records проверяются на разрешимость ссылок к каноническим Part/VIN/Supplier. Отчёт показывает fully-linked / partial / unmatched и покрытие linkage. Неуверенное соответствие не сохраняется автоматически.

### Source-of-truth conflict detection

Система поднимает конфликт, если:

- несколько источников объявлены authoritative для одной reconciliation role;
- authoritative sources дают несовместимые revision claims.

MGC показывает конфликт и evidence, но не выбирает источник истины без корпоративной policy/human decision.

### Integration SLO / SLA view

Добавлена сводка по каждому источнику:

- data-confidence / freshness;
- recent sync success rate;
- quarantine backlog;
- mapping coverage;
- stale mappings / unmatched entities.

### Controlled Pilot Acceptance

`READY_FOR_CONTROLLED_PILOT` выдаётся только при выполнении детерминированных gates. По умолчанию проверяются:

- required source roles присутствуют;
- mapping coverage ≥ 95%;
- stale mappings = 0;
- QMS linkage ≥ порога;
- freshness compliance ≥ 95%;
- recent sync success ≥ 95%;
- quarantine = 0;
- required sources не имеют LOW/UNKNOWN quality;
- source authority не конфликтует;
- EBOM ↔ MBOM = MATCH;
- MES ↔ released configuration = MATCH.

Даже `READY_FOR_CONTROLLED_PILOT` не является production go-live approval: `human_go_live_required = true`.

## API / UX

Добавлены admin API:

- `GET /api/v1/integrations/mappings`;
- `POST /api/v1/integrations/mappings`;
- `PATCH /api/v1/integrations/mappings/{mapping_id}`;
- `POST /api/v1/integrations/reconciliation`.

В admin/integration workspace добавлена компактная карточка **Data Reconciliation · v6.0.3**: Pilot Gate, mapping coverage, EBOM↔MBOM, MES↔Release, QMS linkage, freshness SLO и ключевые blockers. Нового глобального меню нет.

## Governance / boundaries

- reconciliation read-only;
- никаких автоматических write-back в PLM/ERP/MES/QMS;
- stale mapping не используется для сокрытия mismatch;
- source payload не мутируется;
- low confidence не означает automatic rejection;
- contract-invalid payload по-прежнему quarantine через v6.0.2;
- source-of-truth conflict не разрешается автоматически;
- production/pilot go-live всегда human-controlled.

## Ограничение текущей среды

В packaging environment нет корпоративных Teamcenter/Windchill/SAP/MES/QMS endpoints, Docker daemon и Dockle. Поэтому v6.0.3 проверяет reconciliation architecture, deterministic logic, migrations, API/security/build contracts и simulated integration records, но не заявляет, что live corporate integration уже сертифицирована.

Для реального пилота выполнить `docs/INTEGRATION_PILOT_RECONCILIATION.md` и `docs/REAL_INTEGRATION_CHECKLIST.md` на approved integration host.
