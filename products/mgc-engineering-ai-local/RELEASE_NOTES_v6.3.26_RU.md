# Release Notes — MGC Engineering AI Local v6.3.26

## Operations Consolidation & `mgcctl`

v6.3.26 является релизом упрощения эксплуатации. Добавлен единый CLI `mgcctl`, объединяющий operator-facing workflows: status, verify, deploy, rollback, backup, restore, certify, provenance и diagnose.

### Что изменилось

- единый CLI contract `mgc.operations-cli.v1`;
- JSON output и `--dry-run` для автоматизации;
- точные confirmation tokens для destructive/high-impact операций;
- `subprocess.run(..., shell=False)` для делегирования;
- privacy-safe diagnostic report без raw stdout/stderr/argv;
- offline status при отсутствии Docker;
- старые Makefile/scripts сохранены для backward compatibility;
- rolling/blue-green current contract сдвинут на 6.3.25 → 6.3.26;
- DB schema остаётся 6.3.13, миграция не требуется.

### Проверка

- backend regression: **605/605 PASS**;
- test files: **99/99**;
- Operations Consolidation preflight: **31/31 PASS**;
- legacy API contracts: **181/181 preserved**;
- bounded-context routes: **247**;
- API authorization: **317 guarded + 5 explicit system exceptions**;
- Docker security: **38/38**;
- Compose/runtime security: **119/119**;
- Enterprise Security: **23/23**.

### Production status

Release package не выдаёт Production GO. Supply-chain и target-host acceptance остаются отдельными корпоративными gates.

### Supply chain

BUILD_INPUTS: **107 file inputs**, **100 present/hashed**, **7 missing corporate artifacts**, **14 image refs**. SBOM: **37 components**. Status: **CONDITIONAL**, `production_authorized=false`.

### Package integrity

Clean payload: **964 files**; ZIP: **965 members** including `BUILD_MANIFEST.json`; missing/extra/size/hash mismatch: **0/0/0/0**; cache artifacts: **0**; `unzip -t`: **PASS**.
