# MGC Engineering AI Local v6.3.24 — Release Notes

## Acceptance Evidence Registry & Release Provenance Ledger

v6.3.24 добавляет управляемый append-only registry для подписанных release-acceptance артефактов.

### Основные изменения

- content-addressed object store `objects/sha256/<digest>`;
- event ledger с sequence + parent SHA-256;
- exclusive append lock для конкурентных release-processes;
- запрет symlink и overwrite внутри registry;
- регистрация только public keys — private-key material отклоняется;
- `KEY_REGISTERED` / `KEY_REVOKED` без переписывания истории;
- полная криптографическая replay-проверка acceptance/baseline/load signatures по состоянию ключа на момент регистрации;
- revoked key запрещён для новых evidence, но исторические записи до revocation сохраняют валидность;
- approved baseline history;
- cross-version p95/p99/error-rate/throughput/DB-pool/RTO/RPO comparison;
- единый audit report по releases, baselines и trust-key lifecycle;
- optional auto-registration из `release_acceptance_pipeline.py` и `promote_acceptance_baseline.py`;
- Engineering Admin `GET /api/v1/operations/release-provenance` с privacy-safe summary;
- `production_authorized=false` остаётся обязательной границей: registry не выдаёт Production GO.

### Совместимость

- application version: `6.3.24`;
- database schema: `6.3.13`;
- новая DB migration не требуется;
- 247 bounded-context routes сохранены;
- 181/181 legacy API contracts сохранены.

### Проверка

- backend: 573/573 PASS, 97/97 test files;
- provenance preflight: 33/33 PASS;
- architecture/HA/DR/rolling/blue-green/certification gates: PASS;
- API authorization: 317 human-facing routes guarded, 5 explicit system exceptions;
- Docker security 38/38; Compose security 119/119; Enterprise Security 23/23;
- Observability 16/16; Corporate Deployment 13/13; Game Day 15/15; UX 9/9;
- secret scan: 0 findings;
- Compose YAML: 19/19; shell syntax: 28/28; Python compile: PASS.

### Ограничения

Packaging environment не подтверждает WORM-storage, HSM/KMS key custody, corporate immutable-image/CVE approval, реальную target-host load/failover certification или human Production Authorization. Supply chain остаётся `CONDITIONAL`.
