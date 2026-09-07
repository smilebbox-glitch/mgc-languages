# MGC Engineering AI Local v6.3.31 — Resilience Drill Orchestration

## Основное

v6.3.31 добавляет безопасный управляемый контур проверки отказоустойчивости поверх HA, production observability и incident evidence. Это не автономный chaos monkey: система не получает права сама выбирать или запускать destructive faults.

### Добавлено

- `mgc.resilience-drill-plan.v1` — канонический SHA-256 план drill;
- `mgc.resilience-drill-evidence.v1` — канонический SHA-256 execution evidence;
- пять allowlisted сценариев:
  - `api_instance_loss`;
  - `worker_cpu_loss`;
  - `redis_brownout`;
  - `qdrant_brownout`;
  - `integration_gateway_timeout`;
- `mgcctl drill catalog|plan|run|bind|validate`;
- plan-only поведение по умолчанию;
- live execution только с точным `--confirm DRILL`;
- обязательный recovery-step в `finally`;
- bounded requested fault window: 1–120 секунд;
- Redis/Qdrant/integration dependency drill в production заблокирован по умолчанию;
- production dependency override требует одновременно `--allow-production-dependency-drill` и `--maintenance-window-ref`;
- Qdrant drill разрешён только для `ai` / `advanced` профилей;
- simulation evidence получает только `SIMULATED`, никогда `PASS`;
- privacy-safe binding к `mgc.production-incident-evidence.v1` по SHA-256 и bounded signal codes;
- raw incident payloads/summary/details в drill evidence не копируются;
- автоматическое утверждение root cause запрещено;
- production authorization остаётся отдельным человеческим решением.

### Сохранено

- DB schema **6.3.13**; новая DB migration отсутствует;
- PLM/PDM/ERP/MES/QMS source-system writeback остаётся запрещён;
- incident evidence не выполняет destructive recovery и не закрывает incident автоматически;
- PostgreSQL/evidence HA, backup/restore, target-host, load, integration и release certification остаются отдельными воротами;
- 181/181 legacy API contracts сохранены;
- 247 bounded-context automotive routes сохранены.

### Совместимость

- Application: **6.3.31**
- DB schema: **6.3.13**
- New migration: **нет**
- Rolling/Blue-Green adjacent window: **6.3.30 ↔ 6.3.31**
- two-patch rollback: fail-closed

## Верификация

- Backend regression: **652/652 PASS**, **104/104 test-файла**.
- `mgcctl verify --scope full`: **24/24 PASS**.
- Resilience Drill preflight: **13/13 PASS**.
- Operations Consolidation preflight: **32/32 PASS**.
- Python compileall: **PASS**.
- Shell syntax: **29/29 PASS**.
- Compose YAML: **19/19 PASS**.
- Legacy API: **181/181 preserved**, current routes: **247**.

## Supply chain

- BUILD_INPUTS provenance entries: **145/145 validated**;
- present: **138/145**;
- missing corporate lock/wheelhouse artifacts: **7**;
- immutable image refs configured here: **0/14**;
- source-package status: **CONDITIONAL**;
- `production_authorized=false`.

Approved frontend/Python locks, offline wheelhouses, immutable image digests, OS-package receipts and CVE/SCA approvals must be produced on the target corporate build environment.

## Ограничение

Live drill не выполнялся в этой build-среде, потому что target Docker runtime не является корпоративным production/staging host. Программный orchestration contract и simulation path проверены; реальный fault/recovery evidence должен формироваться на разрешённом target-host в утверждённом change/maintenance window.

`production_authorized=false` остаётся обязательным. Supply-chain статус source package формируется отдельно и не может быть повышен drill evidence.

## Упаковка

- controlled payload: **1046 файлов**;
- ZIP members с `BUILD_MANIFEST.json`: **1047**;
- missing/extra/size/hash mismatch: **0**;
- cache artifacts: **0**;
- symlinks: **0**;
- `unzip -t`: **PASS**.
