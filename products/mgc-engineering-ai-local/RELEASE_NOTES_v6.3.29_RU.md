# MGC Engineering AI Local v6.3.29 — Target-Host Deployment Assurance

## Основное

v6.3.29 закрывает следующий production gap после v6.3.28: перед реальным rolling/blue-green deployment система теперь требует проверяемое evidence о целевых application-host. Новых пользовательских экранов и новой DB-схемы нет.

### Что добавлено

- privacy-safe `target_host_probe.py` для каждого application node;
- deterministic `mgc-target-host-assurance-evidence-v1`;
- агрегированный `mgc-target-host-assurance-report-v1`;
- baseline profiles 15/30/100 для CPU/RAM/disk/resource limits;
- проверка Docker CLI/daemon и minimum Docker/Compose contract;
- проверка time synchronization;
- реальный storage write → fsync → read → delete probe;
- one-to-one coverage `node_id` из multi-host topology;
- fail-closed missing/extra/duplicate node handling;
- canonical SHA-256 report integrity;
- optional detached OpenSSL signature;
- `mgcctl certify target-host`;
- rolling/blue-green deployment gate, требующий PASS report;
- dry-run остаётся неразрушающим, но при переданном report валидирует его;
- emergency blue-green rollback не блокируется target-host gate.

### Baseline envelope

| Profile | CPU/node | RAM/node | Free disk/node | Max disk used | `nofile` soft |
|---|---:|---:|---:|---:|---:|
| 15 | 4 cores | 8 GiB | 40 GiB | 90% | 4096 |
| 30 | 4 cores | 8 GiB | 60 GiB | 90% | 4096 |
| 100 | 8 cores | 16 GiB | 100 GiB | 85% | 8192 |

Это **deployment envelope**, а не performance capacity certification. Нагрузочная сертификация 15/30/100 остаётся отдельным контуром.

### Privacy / governance

Probe не собирает hostname, IP-адреса, environment variables или secrets. Даже при `decision=PASS` report сохраняет:

- `production_authorized=false`;
- `performance_certified=false`;
- `human_approval_required=true`.

CVE/SCA, approved locks/wheelhouse, real load/failover evidence, PLM/PDM/ERP/MES/QMS certification и корпоративный change approval остаются отдельными gates.

### Совместимость

- Application: **6.3.29**
- DB schema: **6.3.13**
- New DB migration: **нет**
- Rolling/Blue-Green adjacent window: **6.3.28 ↔ 6.3.29**
- 247 bounded-context automotive routes сохранены
- 181/181 legacy v6.2.0 API contracts сохранены

### Верификация

- Backend: **636/636 PASS**, **102/102 test-файла**
- `mgcctl verify --scope full`: **22/22 PASS**
- Target-Host Assurance preflight: **15/15 PASS**
- Reference target-host certification E2E: **PASS**
- Existing Integration Certification: **49/49 PASS**
- Existing Integration Runtime Assurance: **27/27 PASS**

## Ограничение среды упаковки

В среде сборки нет Docker CLI целевого корпоративного host. Поэтому package проверяет сам механизм target-host evidence/certification/gating, но не подменяет фактический probe ваших серверов. Production authorization остаётся человеческим решением.

## Упаковка

- controlled payload: **1013 файлов**;
- ZIP: **1014 members** с `BUILD_MANIFEST.json`;
- independent manifest verification: missing/extra/size/hash mismatch = **0**;
- cache/test artifacts: **0**;
- ZIP CRC/test: **PASS**.
