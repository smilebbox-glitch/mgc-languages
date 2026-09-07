#!/usr/bin/env python3
"""v6.3.6 static gates for controlled revisions, conflicts and idempotent writes."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def txt(rel): return (ROOT/rel).read_text()
checks=[]
def check(name,ok,detail=''): checks.append((name,bool(ok),detail))

runtime=txt('backend/app/core/runtime_contract.py')
models=txt('backend/app/db/models.py')
migrations=txt('backend/app/db/migrations.py')
uow=txt('backend/app/db/unit_of_work.py')
main=txt('backend/app/main.py')
svc=txt('backend/app/services/revision_control.py')
mq=txt('backend/app/api/contexts/manufacturing_quality.py')
cc=txt('backend/app/api/contexts/configuration_change.py')
ops=txt('backend/app/api/operations_routes.py')
ui=txt('frontend/src/main.tsx')
css=txt('frontend/src/styles.css')

check('release_version','APP_VERSION = "6.3.34"' in runtime)
check('schema_version','SCHEMA_VERSION = "6.3.13"' in runtime)
check('snapshot_model','class EngineeringRevisionSnapshot' in models and 'uq_revision_snapshot_entity_version' in models)
check('idempotency_model','class WriteIdempotencyRecord' in models and 'idempotency_key' in models)
check('conflict_event_model','class EditConflictEvent' in models)
check('approval_unique_model','uq_change_approval_stage_once' in models)
check('migration_v634','def ensure_v634_schema' in migrations and "'6.3.6'" in migrations)
check('migration_duplicate_approval_fail_closed','duplicate approval stage rows exist' in migrations and 'uq_v634_change_approval_stage_once' in migrations)
check('edit_conflict_current_record','current_record' in uow and 'expected_version' in uow and 'current_version' in uow)
check('edit_conflict_http_contract','EDIT_CONFLICT' in main and '"auto_merge": False' in main and 'current_record' in main)
check('visual_diff','def visual_diff' in svc and '"auto_merge": False' in svc)
check('wi_clone_controlled','def clone_work_instruction' in svc and 'status="draft"' in svc and 'translation_status="stale"' in svc)
check('layout_clone_controlled','def clone_layout' in svc and 'StationLayoutPlacement' in svc)
check('idempotency_lookup','def idempotency_lookup' in svc and 'different request' in svc)
check('idempotency_store','def store_idempotency' in svc and 'WriteIdempotencyRecord' in svc)
check('integrity_dashboard','def integrity_dashboard' in svc and 'human_conflict_resolution_required' in svc)
check('wi_idempotency_header','Idempotency-Key' in mq and 'update_work_instruction' in mq)
check('wi_duplicate_approval_block','duplicate approval is blocked' in mq)
check('wi_revision_endpoint','/work-instructions/{instruction_id}/revisions' in mq)
check('wi_diff_endpoint','/work-instructions/{instruction_id}/diff' in mq)
check('layout_revision_endpoint','/layouts/{layout_id}/revisions' in mq)
check('layout_diff_endpoint','/layouts/{layout_id}/diff' in mq)
check('change_diff_endpoint','/changes/{change_id}/diff' in cc and 'candidate_selection_required' in cc)
check('ops_integrity_conflicts','@router.get("/integrity")' in ops and '@router.get("/conflicts")' in ops)
check('frontend_conflict_review','function ConflictReview' in ui and 'Auto-merge отключён' in ui)
check('frontend_revision_diff','function RevisionDiffPanel' in ui and 'Новая ревизия' in ui)
check('frontend_conflict_styles','.conflictReview' in css and '.revisionDiff' in css)
check('frontend_integrity_dashboard',"/api/v1/operations/integrity" in ui and 'Engineering Integrity · v6.3.6' in ui)

failed=[x for x in checks if not x[1]]
for n,ok,d in checks: print(f"{'PASS' if ok else 'FAIL'} {n}"+(f' — {d}' if d else ''))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
