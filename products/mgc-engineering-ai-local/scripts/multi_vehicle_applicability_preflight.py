#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.core.vehicle_applicability import VEHICLE_CLASSES, PROFILE_KEYS

checks=[]
def ck(name,value): checks.append((name,bool(value)))
front=(ROOT/'frontend/src/main.tsx').read_text()
service=(ROOT/'backend/app/services/configuration_management.py').read_text()
schemas=(ROOT/'backend/app/schemas/api.py').read_text()
demo=(ROOT/'demo/seed_demo.py').read_text()

ck('runtime_v6334', APP_VERSION=='6.3.34' and SCHEMA_VERSION=='6.3.13')
ck('vehicle_classes', set(VEHICLE_CLASSES)=={'passenger_car','lcv','truck','bus','special_vehicle','component'})
ck('configuration_keys', all(k in PROFILE_KEYS for k in ['vehicle_class','powertrain_type','drivetrain','wheelbase_mm','axle_configuration','plant','cab_type','gross_vehicle_weight_t','payload_t','battery_kwh']))
ck('schema_vehicle_class','vehicle_class:' in schemas and 'passenger_car|lcv|truck|bus|special_vehicle|component' in schemas)
ck('schema_truck_dimensions','wheelbase_mm:' in schemas and 'gross_vehicle_weight_t:' in schemas and 'payload_t:' in schemas)
ck('serializer_profile','"vehicle_class": profile.get("vehicle_class")' in service and '"configuration": profile' in service)
ck('workspace_multi_vehicle','"multi_vehicle"' in service and '"class_counts"' in service)
ck('unknown_fail_closed','unknown_is_not_included' in service)
ck('frontend_classes','Легковой автомобиль' in front and 'Грузовой автомобиль' in front)
ck('frontend_truck_fields','Колёсная база, мм' in front and 'GVW, т' in front and 'Payload, т' in front and 'Тип кабины' in front)
ck('demo_passenger','DEMO-PASSENGER' in demo and 'PC-BEV-AWD' in demo)
ck('demo_truck','DEMO-TRUCK' in demo and 'TRK-6X4-D13-AMT' in demo and 'TRK-4X2-D11-AMT' in demo)
ck('demo_applicability','configurations/applicability' in demo)
ck('no_db_migration',not any((ROOT/'backend/app/db/migrations/versions').glob('*6.3.34*')) if (ROOT/'backend/app/db/migrations/versions').exists() else True)
failed=[n for n,v in checks if not v]
for n,v in checks: print(('PASS' if v else 'FAIL'),n)
print(f'\nMulti-vehicle applicability preflight: {len(checks)-len(failed)}/{len(checks)} PASS')
if failed: raise SystemExit('failed: '+', '.join(failed))
