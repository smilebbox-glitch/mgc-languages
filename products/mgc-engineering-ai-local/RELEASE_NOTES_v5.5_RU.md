# MGC Engineering AI Local v5.5.0

## Configuration & Release Assurance

v5.5 связывает engineering configuration с manufacturing planning и фактической конфигурацией изделия, не подменяя PLM/PDM, ERP или MES.

### Основные функции

- детерминированная сверка **EBOM ↔ MBOM**: missing/extra/revision/quantity/unit/supplier mismatch;
- явная **150% → 100% Vehicle Variant configuration**; `UNKNOWN` никогда не считается применимостью;
- **Effectivity Management** по variant / plant / supplier / VIN / serial / date;
- **Change Cut-In Control**: cut-in point, old stock disposition, logistics confirmation, PPAP target revision;
- **AS-DESIGNED → AS-PLANNED → AS-BUILT** с контролируемыми deviation/waiver;
- **Buildability Check** и Engineering → Manufacturing Handover gate;
- **Configuration Release Package v2** с SHA-256 fingerprint инженерного и manufacturing/configuration snapshot;
- **Release Baseline v3** фиксирует MBOM, effectivity, cut-in и supersession; Release Drift видит изменения manufacturing configuration после freeze;
- Cross-System Consistency, Variant/Plant Matrix, supersession/interchangeability/stock-use evidence;
- deterministic **Ask Configuration**, работающий на CPU без LLM.

### Governance

- PLM/PDM — authoritative EBOM/product definition;
- ERP/manufacturing planning — authoritative MBOM/material planning;
- MES/import — authoritative AS-BUILT observation;
- MGC — engineering intelligence/evidence layer;
- shadow/configuration-authority writes через human API требуют Engineering Admin;
- нет автоматического release/SOP approval, stock transaction, ERP/MES/PLM write-back или machine control.

### Security

Все новые cross-domain представления сохраняют Project / Manufacturing Area / Document ACL. Evidence-bearing entity с любым скрытым evidence fail-closed и не раскрывается частично.

### CPU

Все reconciliation/effectivity/buildability/drift функции детерминированы и работают без GPU/LLM.
