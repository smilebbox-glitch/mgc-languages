#!/usr/bin/env python3
"""v6.3.3 static gates for optimistic concurrency, UoW and domain integrity."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.models import ChangeRequest, ProcessStation, WorkInstruction, ManufacturingLayout

checks=[]
def check(name,ok,detail=''): checks.append((name,bool(ok),detail))
check('release_version',APP_VERSION=='6.3.34',APP_VERSION)
check('schema_version',SCHEMA_VERSION=='6.3.13',SCHEMA_VERSION)
for name,model in [('change',ChangeRequest),('station',ProcessStation),('wi',WorkInstruction),('layout',ManufacturingLayout)]:
    check(f'{name}_row_version',hasattr(model,'row_version'))
    check(f'{name}_orm_versioning',model.__mapper__.version_id_col is not None)

uow=(ROOT/'backend/app/db/unit_of_work.py').read_text()
models=(ROOT/'backend/app/db/models.py').read_text()
migrations=(ROOT/'backend/app/db/migrations.py').read_text()
main=(ROOT/'backend/app/main.py').read_text()
audit=(ROOT/'backend/app/services/audit.py').read_text()
change=(ROOT/'backend/app/services/engineering_change.py').read_text()
mq=(ROOT/'backend/app/api/contexts/manufacturing_quality.py').read_text()
schemas=(ROOT/'backend/app/schemas/api.py').read_text()
front=(ROOT/'frontend/src/main.tsx').read_text()
check('unit_of_work', 'class UnitOfWork' in uow and 'StaleDataError' in uow)
check('structured_edit_conflict','EDIT_CONFLICT' in main and '@app.exception_handler(EditConflict)' in main)
check('expected_version_contract','expected_version' in schemas and 'expected_layout_version' in schemas)
check('wi_expected_version_enforced','require_expected_version(row, expected_version, "work_instruction")' in mq)
check('station_expected_version_enforced','require_expected_version(station, expected_version, "process_station")' in mq)
check('layout_expected_version_enforced','require_expected_version(layout, req.expected_layout_version, "manufacturing_layout")' in mq)
check('audit_noncommitting_primitive','def add_audit_event' in audit)
check('wi_audit_atomic','add_audit_event' in mq and 'with UnitOfWork(db) as uow' in mq)
check('change_event_atomic','def add_change_event' in change and change.count('with UnitOfWork(db) as uow') >= 5)
check('change_state_row_lock','ChangeEventState).where' in change and 'with_for_update()' in change)
check('fresh_db_constraints',all(x in models for x in ('ck_bom_quantity_positive','ck_process_station_headcount_positive','ck_work_instruction_cycle_nonnegative')))
check('legacy_db_constraints','v6.3.3 migration blocked' in migrations and 'trg_v633_bom_guard_i' in migrations and 'pg_constraint' in migrations)
check('migration_marker','def ensure_v633_schema' in migrations and "'6.3.3'" in migrations)
check('frontend_sends_expected_version','expected_version:instructionForm.row_version' in front and 'expected_layout_version:layout?.row_version' in front)
check('frontend_conflict_message','EDIT_CONFLICT' in front)
for n,o,d in checks: print(f"{'PASS' if o else 'FAIL'} {n}"+(f' — {d}' if d else ''))
failed=[x for x in checks if not x[1]]
print(f'SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS')
raise SystemExit(1 if failed else 0)
