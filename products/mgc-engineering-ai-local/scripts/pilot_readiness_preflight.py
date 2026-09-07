#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.runtime_contract import APP_VERSION,SCHEMA_VERSION

checks=[]
def ck(name,value): checks.append((name,bool(value)))
front=(ROOT/'frontend/src/main.tsx').read_text()
styles=(ROOT/'frontend/src/styles.css').read_text()
workspace=(ROOT/'backend/app/services/project_workspace.py').read_text()
mgc=(ROOT/'scripts/mgcctl.py').read_text()

ck('runtime_v6333', APP_VERSION=='6.3.34' and SCHEMA_VERSION=='6.3.13')
nav=front.split('const NAV:',1)[1].split('function Viewer',1)[0]
for label in ['Главная','Проекты','Детали / BOM','Инструкции','Поиск / ИИ']:
    ck('primary_nav_'+label.replace(' ','_').replace('/','_'), label in nav)
ck('specialist_tabs_hidden_from_primary_nav','Object 360' not in nav and 'Изменения' not in nav)
ck('action_center_backend_contract','"action_center"' in workspace and 'human_decision_required' in workspace and 'project_readiness_evidence' in workspace)
ck('action_center_bounded','action_center = action_center[:12]' in workspace)
ck('home_action_center','Action Center' in front and 'homeActions' in front)
ck('project_focus_workspace','ProjectFocusWorkspace' in front and 'evidence-backed' in front)
ck('progressive_disclosure','className="projectAdvanced"' in front and 'Полная инженерная картина' in front)
ck('admin_it_separation','Для IT' in front and "me.is_admin" in front)
ck('responsive_productization','v6.3.34 Pilot Readiness & UX Simplification' in styles and '@media(max-width:760px)' in styles)
ck('no_db_migration',not any((ROOT/'backend/app/db/migrations/versions').glob('*6.3.34*')) if (ROOT/'backend/app/db/migrations/versions').exists() else True)
ck('full_verify_includes_pilot_readiness','pilot-readiness' in mgc and 'pilot_readiness_preflight.py' in mgc)
failed=[name for name,value in checks if not value]
for name,value in checks: print(('PASS' if value else 'FAIL'),name)
print(f'\nPilot readiness & UX simplification preflight: {len(checks)-len(failed)}/{len(checks)} PASS')
if failed: raise SystemExit('failed: '+', '.join(failed))
