# MGC Engineering AI Local v6.3.5
## Engineering Approval & Release Governance

v6.3.5 — технический governance-релиз поверх v6.3.4. Он добавляет управляемые матрицы согласования, maker-checker / 4-eyes, segregation of duties, tamper-evident approval records и единый Release Package для передачи утверждённого инженерного набора в производство.

## Главное
- configurable approval policy по типу объекта, проекту и Manufacturing Area;
- frozen policy snapshot на каждый approval cycle;
- default 2-stage 4-eyes policy: Engineering Review → Final Release;
- запрет self-approval автора;
- запрет одному approver выполнять несколько этапов при включённом SoD;
- SHA-256 snapshot объекта при submit;
- hash-chained approval records (`previous_hash` / `record_hash`);
- fail-closed approval при изменении объекта после submit;
- новые controlled Release Packages;
- Release Package не может использоваться для обхода approval WI/layout/change;
- повторная проверка всех package snapshot перед release;
- controlled supersession старых MGC WI/layout revisions;
- PLM/PDM BOM/document evidence никогда не модифицируется при release;
- production write-back не выполняется автоматически;
- квалифицированная электронная подпись не заявляется.

## Новые таблицы
- `engineering_approval_policies`
- `engineering_approval_cases`
- `engineering_approval_records`
- `engineering_release_packages`
- `engineering_release_package_items`

## Версии
- Application: `6.3.5`
- Schema: `6.3.5`

## API
В шести bounded contexts теперь 209 routes. Все 181 legacy v6.2.0 method/path contracts сохранены.

Новые поверхности:
- approval policy administration;
- submit/get/decision approval cases;
- governance summary;
- create/list/get/submit/release Engineering Release Packages.

## Совместимость
Существующий Engineering Change approval workflow сохранён. Для Work Instructions прямой admin approval по умолчанию отключён (`ALLOW_LEGACY_DIRECT_WI_APPROVAL=false`): используется controlled approval workflow. Временный legacy mode можно включить явно, но при active approval policy прямой approval всё равно блокируется.

## Production boundary
Release Package — это engineering handover record. MGC не выдаёт PLC/robot/MES commands и не выполняет автоматический write-back в PLM/PDM/MES.
