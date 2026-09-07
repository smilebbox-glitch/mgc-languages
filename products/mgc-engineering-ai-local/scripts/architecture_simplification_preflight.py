#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION, BOUNDED_CONTEXTS, PROFILE_FEATURES, RuntimeConfigurationError, active_bounded_contexts, available_object_types, runtime_contract

checks=[]
def check(name, ok, detail=""):
    checks.append((name,bool(ok),detail))

check('release_version', APP_VERSION=='6.3.34', APP_VERSION)
check('schema_current', SCHEMA_VERSION=='6.3.13', SCHEMA_VERSION)
check('six_bounded_contexts', len(BOUNDED_CONTEXTS)==6, str(sorted(BOUNDED_CONTEXTS)))
check('profile_monotonicity', PROFILE_FEATURES['core'] < PROFILE_FEATURES['ai'] < PROFILE_FEATURES['advanced'])
core=runtime_contract(Settings(deployment_profile='core', readiness_require_qdrant=True, graph_enabled=True, object_store_enabled=True))
ai=runtime_contract(Settings(deployment_profile='ai', readiness_require_qdrant=True))
adv=runtime_contract(Settings(deployment_profile='advanced', readiness_require_qdrant=True, graph_enabled=True, object_store_enabled=True))
check('core_postgres_required', core['dependencies']['postgres']['required'])
check('core_qdrant_optional', not core['dependencies']['qdrant']['required'])
check('core_neo4j_optional', not core['dependencies']['neo4j']['required'])
check('ai_qdrant_required', ai['dependencies']['qdrant']['required'])
check('advanced_graph_supported', adv['dependencies']['neo4j']['required'])
check('postgres_core_invariant', all('postgres_core' in PROFILE_FEATURES[x] for x in PROFILE_FEATURES))
check('core_object360_surface', 'supplier' not in available_object_types(PROFILE_FEATURES['core']) and 'vin' in available_object_types(PROFILE_FEATURES['core']))
check('core_context_surface', 'supplier_field' not in active_bounded_contexts(PROFILE_FEATURES['core']) and 'intelligence_search' in active_bounded_contexts(PROFILE_FEATURES['core']))
try:
    runtime_contract(Settings(deployment_profile='typo-profile'))
    invalid_profile_closed=False
except RuntimeConfigurationError:
    invalid_profile_closed=True
check('invalid_profile_fail_closed', invalid_profile_closed)

compose=yaml.safe_load((ROOT/'docker-compose.yml').read_text())
services=compose.get('services',{})
check('qdrant_profiled', set(services.get('qdrant',{}).get('profiles',[]))=={'ai','advanced'})
check('model_server_profiled', set(services.get('model-server',{}).get('profiles',[]))=={'ai','advanced'})
check('neo4j_advanced_only', services.get('neo4j',{}).get('profiles')==['advanced'])
api_deps=set((services.get('api',{}).get('depends_on') or {}).keys())
check('api_no_optional_hard_dependency', not ({'qdrant','model-server','neo4j','minio'} & api_deps), str(sorted(api_deps)))
check('core_profile_default', services.get('api',{}).get('environment',{}).get('DEPLOYMENT_PROFILE')=='${DEPLOYMENT_PROFILE:-core}')

routes=(ROOT/'backend/app/api/simplified_routes.py').read_text()
check('object360_api', '/objects/{object_type}/{object_id:path}' in routes)
check('runtime_api', '@router.get("/runtime")' in routes)
check('connector_contract_api', '@router.get("/connector-contract")' in routes)
frontend=(ROOT/'frontend/src/main.tsx').read_text()
check('pilot_primary_nav', all(x in frontend.split('function Viewer',1)[0] for x in ["label: 'Главная'","label: 'Проекты'","label: 'Детали / BOM'","label: 'Инструкции'","label: 'Поиск / ИИ'"]))
check('specialist_tabs_not_primary_nav', "label: 'Object 360'" not in frontend.split('function Viewer',1)[0] and "label: 'Изменения'" not in frontend.split('function Viewer',1)[0] and "label: 'Документы'" not in frontend.split('function Viewer',1)[0])
check('capability_gate', (ROOT/'backend/app/core/capability_gate.py').exists())
gate=(ROOT/'backend/app/core/capability_gate.py').read_text()
check('supplier_surface_gated', 'supplier-localization|localization' in gate and 'supplier_field' in gate)
check('native_cad_surface_gated', 'native-formats|convert' in gate and 'native_cad_gateway' in gate)
check('generic_pre_auth_404', 'json.dumps({"detail": "Not found"})' in gate)

failed=[x for x in checks if not x[1]]
for name,ok,detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ''))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: sys.exit(1)
