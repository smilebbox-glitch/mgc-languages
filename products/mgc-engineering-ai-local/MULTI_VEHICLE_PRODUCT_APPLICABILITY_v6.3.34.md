# MGC Engineering AI Local v6.3.34 - Multi-Vehicle Product Applicability

Application: **6.3.34**  
Database schema: **6.3.13**  
Migration: **none**

## Цель релиза

v6.3.34 расширяет существующий engineering Digital Thread с легковых автомобилей на несколько классов автомобильной продукции без создания отдельных систем и без нового источника истины.

Поддерживаемые классы варианта:

- `passenger_car` - легковой автомобиль;
- `lcv` - лёгкий коммерческий автомобиль;
- `truck` - грузовой автомобиль;
- `bus` - автобус;
- `special_vehicle` - специальная техника;
- `component` - компонент/агрегат как самостоятельная продуктовая программа.

## Единая модель продукта

Релиз переиспользует существующие сущности:

- `VehicleVariant` - конкретная конфигурация автомобиля/продукта;
- `ConfigurationApplicability` - явная применимость инженерного объекта к варианту;
- `attributes_json` - расширяемые конфигурационные свойства варианта.

Новых таблиц БД не добавлено. Canonical vehicle profile нормализуется в API/read-model поверх существующего `attributes_json`.

## Canonical configuration profile

В v6.3.34 стандартизированы следующие атрибуты:

- `vehicle_class`;
- `powertrain_type`;
- `drivetrain`;
- `wheelbase_mm`;
- `axle_configuration`;
- `plant`;
- `cab_type`;
- `gross_vehicle_weight_t`;
- `payload_t`;
- `battery_kwh`.

Существующие поля `model_year`, `market`, `body_style`, `engine`, `transmission`, `trim` сохранены для обратной совместимости.

## Применимость

Применимость BOM/WI/document/change/process/quality evidence должна быть явной:

`engineering object -> ConfigurationApplicability -> VehicleVariant`

Безопасное правило: **UNKNOWN не означает applies-to-all**.

Например, изменение для `TRK-6X4-D13-AMT` не распространяется автоматически на `TRK-4X2-D11-AMT`, даже если оба варианта относятся к одной модели грузовика.

## Легковой пример

Demo project: `DEMO-PASSENGER`  
Part: `8450012345`  
Change: `Rev C -> Rev D`  
Variant: `PC-BEV-AWD`

Configuration:
- passenger car;
- BEV;
- AWD;
- wheelbase 2850 mm;
- battery 82 kWh;
- RU/EAEU market;
- MGC Demo Plant.

Сценарий связывает BOM diff, drawing/STEP, ECR, WI, assembly station и evidence в один Digital Thread.

## Грузовой пример

Demo project: `DEMO-TRUCK`  
Part: `6300012345`  
Change: `Rev A -> Rev B`  
Primary variant: `TRK-6X4-D13-AMT`

Configuration:
- truck;
- ICE;
- 6x4;
- wheelbase 3900 mm;
- D13 / 12AMT;
- sleeper high-roof cab;
- GVW 40 t;
- payload 20 t;
- MGC Demo Plant.

Comparison variant: `TRK-4X2-D11-AMT` with a different axle formula, wheelbase, cab and weight envelope. This demonstrates why applicability is configuration-specific.

## Safety and authority boundaries

- MGC remains an engineering intelligence/digital-thread layer, not a vehicle homologation authority.
- PLM/PDM/ERP/MES/QMS remain authoritative where configured.
- Applicability does not self-approve BOM/WI/ECO release.
- AI can explain/filter evidence but cannot invent vehicle applicability.
- Human engineering approval remains mandatory.
- Existing ACL/audit/release governance is unchanged.

## Compatibility

- DB schema remains **6.3.13**;
- no migration;
- API route count does not increase;
- legacy API contract remains preserved;
- adjacent rolling/blue-green window: **6.3.33 <-> 6.3.34**;
- v6.3.32/v6.3.33 resilience controls remain mandatory deployment safeguards.
