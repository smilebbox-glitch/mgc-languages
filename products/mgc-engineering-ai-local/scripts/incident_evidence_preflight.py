#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok): checks.append((name,bool(ok)))
def txt(path): return (ROOT/path).read_text(encoding='utf-8')

rt=txt('backend/app/core/runtime_contract.py')
cfg=txt('backend/app/core/config.py')
core=txt('backend/app/core/incident_evidence.py')
support=txt('backend/app/services/production_support.py')
routes=txt('backend/app/api/operations_routes.py')
tasks=txt('backend/app/workers/tasks.py')
celery=txt('backend/app/workers/celery_app.py')

def has(p,s): return s in txt(p)

ck('runtime_v6330', 'APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('canonical_schema', 'mgc.production-incident-evidence.v1' in core)
ck('canonical_integrity', 'payload_sha256' in core and 'validate_incident_evidence' in core)
ck('bounded_signal_fingerprint', 'signal_fingerprint' in core and 'sha256' in core)
ck('privacy_no_raw_logs', '"contains_raw_logs": False' in core)
ck('privacy_no_documents', '"contains_document_content": False' in core)
ck('privacy_no_queries', '"contains_queries": False' in core)
ck('privacy_no_credentials', '"contains_credentials": False' in core)
ck('no_auto_destructive_recovery', '"automatic_destructive_recovery": False' in core)
ck('no_auto_resolution', '"automatic_incident_resolution": False' in core and 'Resolved incidents are never reopened or closed automatically' in support)
ck('not_production_authorization', '"production_authorized": False' in core)
ck('human_operator_boundary', '"human_operator_required": True' in core and 'human_operator_required' in support)
ck('feature_gate_default_off', 'automated_incident_materialization_enabled: bool = False' in cfg)
ck('periodic_evidence_capture', 'incident_evidence_snapshot(db, readiness=readiness)' in tasks)
ck('periodic_materialization_gated', 'if get_settings().automated_incident_materialization_enabled:' in tasks)
ck('sampling_schedule_bounded', 'operational_sampling_enabled' in celery and 'max(cfg.operational_sampling_interval_seconds, 30)' in celery)
ck('support_bundle_contains_evidence', '"incident-evidence.json": incident_evidence' in support)
ck('support_bundle_strips_operator_narrative', '_privacy_safe_support_operations' in support and '"operator_narrative_exported": False' in support)
ck('prometheus_bounded_severity', 'mgc_incident_evidence_signals' in support and '["severity"]' in support)
ck('admin_evidence_endpoint', '@router.get("/incident-evidence")' in routes and 'def incident_evidence' in routes)
ck('admin_reconcile_endpoint', '@router.post("/incident-evidence/reconcile")' in routes and 'materialize=None' in routes)
ck('no_v6330_db_migration', 'ensure_v6330_schema' not in txt('backend/app/db/migrations.py'))
ck('regression_tests_present', (ROOT/'backend/tests/test_v6330_production_observability_incident_evidence.py').exists())

failed=[n for n,ok in checks if not ok]
for n,ok in checks: print(f"{'PASS' if ok else 'FAIL'}  {n}")
print(f"\nProduction observability / incident-evidence preflight: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit('failed: '+', '.join(failed))
