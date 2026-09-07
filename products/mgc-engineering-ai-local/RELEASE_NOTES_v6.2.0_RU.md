# MGC Engineering AI Local v6.2.0
## Architecture Simplification Release

v6.2.0 — архитектурный релиз упрощения после production-hardening v6.0.x и Corporate Deployment Kit v6.1.0. Новых automotive business-domain функций релиз не добавляет. Цель — уменьшить связанность, число обязательных runtime-компонентов и когнитивную сложность, сохранив существующие API и инженерные возможности.

## Главное

- modular monolith вместо дробления на микросервисы;
- шесть формализованных bounded contexts: `engineering_core`, `configuration_change`, `manufacturing_quality`, `supplier_field`, `intelligence_search`, `platform_operations`;
- центральный runtime contract для версии, schema marker, deployment profile и capability policy;
- PostgreSQL закреплён как обязательный MGC core store;
- Qdrant и Neo4j переведены в optional/rebuildable projections;
- единый Evidence contract с fail-closed visibility;
- единый Action/Decision contract для нормализации действий и решений;
- единый Connector envelope для PLM/PDM/ERP/MES/QMS adapters;
- Object 360 стал основной объектной UX-surface;
- primary navigation сокращена до `Сегодня / Проекты / Object 360 / Изменения / Поиск-ИИ`;
- advanced surfaces остаются через drill-down и feature/capability gates;
- три runtime profile: `core`, `ai`, `advanced`;
- graceful degradation search/RAG: Core работает без Qdrant/model-server и использует deterministic metadata/lexical fallback;
- profile composition не расширяет ACL и не заменяет authorization;
- DR-модель упрощена: PostgreSQL + evidence storage — authoritative backup set; Qdrant snapshot optional/rebuildable, Neo4j/Redis/model weights не authoritative;
- старые API/schema contracts сохраняются для пошаговой миграции без big-bang rewrite.

## Runtime profiles

### Core

Минимальная платформа: PostgreSQL, Redis jobs, evidence storage, core engineering/configuration/manufacturing-quality capabilities, Object 360, Evidence, Actions/Decisions, connectors и lexical/metadata search. Qdrant, Neo4j и generative model server не являются обязательными.

### AI

Core + Qdrant, embeddings/reranker, semantic search и локальные LLM/VLM возможности. При недоступности AI-компонента core engineering functionality не должна исчезать.

### Advanced

AI + Neo4j projection, advanced supplier/field/program/cost/native-CAD capabilities и расширенные deployment components.

Профили монотонны (`Core ⊂ AI ⊂ Advanced`) и являются runtime composition policy, а не permission model.

## Object 360

Добавлен упрощённый API/UX facade для объектов `part`, `vin`, `change`, `defect`, `requirement`, `supplier`. Object 360 объединяет identity, summary, sections, evidence и normalized actions. Evidence и cross-domain sections применяют существующий fail-closed ACL: скрытый исходный документ не раскрывается через агрегированное представление.

## Platform contracts

### Evidence

`EvidenceRef` и общий Evidence bundle делают provenance единообразным для доменов. При смешанном visible/hidden evidence bundle формируется fail-closed.

### Action / Decision

Доменные warnings/recommendations/decisions нормализуются в единый action schema. Decision всегда сохраняет `human_decision_required=true`.

### Connector envelope

External source adapters используют общий envelope с source, entity type, external ID, revision/timestamp и payload/provenance. Внешняя система остаётся authoritative owner своих данных.

## Deployment simplification

Базовый Compose запускается как Core. Optional компоненты подключаются Compose profiles `ai` и `advanced`. Старые `make up/cpu/gpu/start` сохранены и используют центральный deployment profile; добавлены `make profile-core`, `make profile-ai`, `make profile-advanced`.

## DR simplification

Authoritative backup:

- PostgreSQL;
- evidence storage.

Optional snapshot:

- Qdrant index, если semantic profile активен и snapshot доступен.

Rebuildable/transient и не считаются authoritative backup:

- Redis queue;
- Neo4j projection;
- local model weights;
- container images.

## Verification

- pre-hardening backend baseline: 324/324 PASS;
- dedicated v6.2.0 architecture tests после hardening: 11/11 PASS;
- post-hardening changed-surface regression: 31/31 PASS;
- architecture simplification preflight: 25/25 PASS;
- human-facing authorization: 236/236 guarded, 4 explicit exceptions;
- Docker static security: 38/38 PASS;
- Compose/runtime security: 100/100 PASS;
- Enterprise Security: 23/23 PASS;
- Observability: 16/16 PASS;
- Game Day: 15/15 PASS;
- Corporate Deployment: 13/13 PASS;
- UX acceptance: 9/9 PASS;
- Compose YAML: 13/13 PASS;
- source secret scan: 0 findings;
- declared-component SBOM: 37 components;
- Core/AI backup-manifest semantics: PASS;
- Python compileall, shell syntax, TS/TSX transpile: PASS.

Dependency lock remains intentionally unresolved in this packaging environment: frontend `package-lock.json` is absent and backend requirements contain 25 declared ranges. Approved corporate npm mirror/wheelhouse and real CVE/image scans remain target-build-host gates.

Реальные Docker build, Dockle, Trivy/Grype, AD/OIDC/PKI tests, target-host restore/load tests и PLM/ERP/MES/QMS connectivity не выполнялись в packaging environment.

Полный backend suite после этого hardening-pass был запущен повторно, но упаковочный runtime достиг лимита исполнения после 44% тестов. Поэтому новый результат 324/324 не заявляется: 324/324 относится к исходному v6.2.0 baseline, а для hardening-pass подтверждены 11/11 dedicated architecture, 31/31 changed-surface regression и перечисленные production/security preflight gates. Полный suite остаётся обязательным CI gate на approved build host.


## Hardening pass — profile integrity и реальное сокращение surface

После первого architecture-simplification pass добавлено fail-closed поведение runtime composition:

- неизвестный `DEPLOYMENT_PROFILE` больше не откатывается молча в `advanced`; конфигурация завершается явной ошибкой;
- `FEATURES_ENABLED` не может расширить `core`/`ai` capability из более высокого профиля; для расширения нужно явно выбрать профиль;
- capability gate переведён на единый декларативный registry и теперь закрывает Supplier/Localization, Field, Cost, Program Control, Neo4j graph, Native CAD gateway и VLM surfaces;
- до аутентификации gate отвечает generic 404 и не раскрывает feature/deployment posture;
- Object 360 catalog строится из активных capabilities; Supplier скрыт вне `advanced`;
- VIN/Object 360 остаётся доступным в Core, но не подтягивает Field Claim evidence, если `supplier_field` не активен;
- `/api/v1/runtime` теперь показывает capability→bounded-context map, доступные Object 360 types и диагностику runtime overrides.

Это не меняет ACL/RBAC и не превращает deployment profile в permission model. Цель — чтобы Core действительно был меньшей operational surface, а не только меньшим Compose-графом.
