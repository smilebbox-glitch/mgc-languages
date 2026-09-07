#!/usr/bin/env python3
"""Static fail-closed checks for v6.3.9 Database Performance & Scale Hardening."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok, detail=""):
    checks.append((name,bool(ok),detail))

def text(path): return (ROOT/path).read_text()
rt=text('backend/app/core/runtime_contract.py'); cfg=text('backend/app/core/config.py'); session=text('backend/app/db/session.py')
perf=text('backend/app/core/db_performance.py'); gov=text('backend/app/services/performance_governance.py')
mig=text('backend/app/db/migrations.py'); bom=text('backend/app/services/bom.py'); outbox=text('backend/app/services/projection_outbox.py')
routes=text('backend/app/api/contexts/platform_operations.py'); reqlog=text('backend/app/core/request_logging.py')
ck('version','APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('migration','def ensure_v639_schema' in mig and "'6.3.9'" in mig)
ck('composite indexes',all(x in mig for x in ('idx_v639_documents_project_area_created','idx_v639_bom_parent_rev_child','idx_v639_wi_scope_station_status','idx_v639_projection_claim')))
ck('bounded pool config',all(x in cfg for x in ('db_pool_size','db_max_overflow','db_pool_timeout_seconds','db_pool_recycle_seconds')))
ck('pool applied',all(x in session for x in ('pool_size','max_overflow','pool_timeout','pool_recycle')))
ck('slow query telemetry','mgc_db_slow_queries_total' in perf and 'sql_text_stored' in perf and 'bind_values_stored' in perf)
ck('request query budget',all(x in perf for x in ('db_query_budget_max_statements','DB_QUERY_BUDGET_WARNINGS','QueryBudgetExceeded')) and 'begin_request_budget' in reqlog)
ck('hard budget default off','db_query_budget_enforcement_enabled: bool = False' in cfg)
ck('n+1 heuristic','mgc_db_statements_per_request' in perf)
ck('cursor pagination','encode_cursor' in gov and 'decode_cursor' in gov and '/audit/cursor' in routes)
ck('cursor bounded limits','cursor_page_default_limit' in cfg and 'cursor_page_max_limit' in cfg)
ck('bulk bom insert','insert(BOMItem)' in bom and 'bulk_ingest_batch_size' in bom)
ck('bulk search chunks','insert(DocumentSearchChunk)' in outbox and 'bulk_ingest_batch_size' in outbox)
ck('scale profiles',all(x in gov for x in ('pilot_15','pilot_30','enterprise_100')))
ck('no capacity claim','production_capacity_claim' in gov and 'certification_required' in gov)
ck('operations endpoint','/operations/performance' in routes)
ck('operations support bundle','database_performance' in text('backend/app/services/production_support.py'))
ck('env knobs',all(x in text('.env.example') for x in ('DB_POOL_SIZE','DB_SLOW_QUERY_MS','PERFORMANCE_SCALE_PROFILE')))
failed=[x for x in checks if not x[1]]
for name,ok,detail in checks: print(f"{'PASS' if ok else 'FAIL'} {name}"+(f' — {detail}' if detail else ''))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
