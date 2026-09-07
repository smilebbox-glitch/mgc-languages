# MGC Engineering AI Local v6.3.34 - Release Notes

## Multi-Vehicle Product Applicability

v6.3.34 расширяет единый Engineering Digital Thread на легковые и коммерческие транспортные средства без создания отдельных приложений и без миграции БД.

### Добавлено

- canonical `Vehicle Class`: Passenger Car, LCV, Truck, Bus, Special Vehicle, Component;
- canonical configuration attributes: powertrain, drivetrain, wheelbase, axle configuration, plant, cab, GVW, payload, battery;
- нормализованный `configuration` read-model в существующем Vehicle Variant API;
- class counts / multi-vehicle scope в Configuration Workspace;
- explicit variant applicability с правилом `UNKNOWN != applies-to-all`;
- UI для создания/просмотра passenger и commercial vehicle configurations;
- отдельный fail-closed `multi-vehicle-applicability` release preflight;
- demo с двумя связанными сценариями: `DEMO-PASSENGER` и `DEMO-TRUCK`.

### Демо: легковой автомобиль

- Project: `DEMO-PASSENGER`
- Part: `8450012345`
- Rev C -> Rev D
- Variant: `PC-BEV-AWD`
- BEV / AWD / 2850 mm / 82 kWh
- BOM, drawing/3D, ECR, WI, station/operation, Digital Thread.

### Демо: грузовой автомобиль

- Project: `DEMO-TRUCK`
- Part: `6300012345`
- Rev A -> Rev B
- Variant: `TRK-6X4-D13-AMT`
- 6x4 / 3900 mm / D13 / 12AMT / sleeper cab / GVW 40 t / payload 20 t
- comparison variant: `TRK-4X2-D11-AMT`.

### Архитектурное решение

Новых таблиц и нового master-data слоя нет. v6.3.34 переиспользует существующие `VehicleVariant`, `ConfigurationApplicability` и `attributes_json`. PLM/ERP/MES/QMS authority boundaries остаются прежними.

### Совместимость

- Application: **6.3.34**
- DB schema: **6.3.13**
- Migration: **none**
- Adjacent rollout: **6.3.33 <-> 6.3.34**
- Existing API routes are preserved; no new multi-vehicle route is required.

### Verification status

Backend regression and release-gate counts are recorded in `VERIFICATION_v6.3.34.md`. Corporate supply-chain artifacts remain a separate production authorization requirement; no missing corporate hashes/digests are fabricated.

### Финальная упаковка

- controlled release payload: **1095 файлов**;
- ZIP: **1096 members** вместе с `BUILD_MANIFEST.json`;
- missing/extra/size/SHA mismatch: **0/0/0/0**;
- cache artifacts: **0**;
- symlinks: **0**;
- ZIP CRC: **PASS**.

Demo-ready пакет поставляется отдельно и содержит два синтетических сценария Passenger + Truck и три обновлённых PDF для руководства, IT-директора и автора демонстрации.
