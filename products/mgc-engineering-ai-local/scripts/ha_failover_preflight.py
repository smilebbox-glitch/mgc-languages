#!/usr/bin/env python3
"""Static fail-closed verification for v6.3.34 High Availability & Failover Coordination."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,ok): checks.append((name,bool(ok)))
def text(rel): return (ROOT/rel).read_text()
rt=text('backend/app/core/runtime_contract.py'); cfg=text('backend/app/core/config.py')
ha=text('backend/app/core/high_availability.py'); ops=text('backend/app/api/operations_routes.py')
support=text('backend/app/services/production_support.py'); compose=text('docker-compose.yml')
overlay=text('docker-compose.ha.yml'); gw=text('ops/gateway/templates/ha.conf.template')
beat=text('backend/app/workers/singleton_beat.py'); celery=text('backend/app/workers/celery_app.py')
drill=text('scripts/ha_failover_drill.sh') if (ROOT/'scripts/ha_failover_drill.sh').exists() else ''
ck('app_6318','APP_VERSION = "6.3.34"' in rt); ck('schema_6313','SCHEMA_VERSION = "6.3.13"' in rt)
ck('ha_default_off','ha_enabled: bool = False' in cfg); ck('api_min_two','ha_min_api_replicas: int = 2' in cfg)
ck('worker_min_two','ha_min_worker_replicas_per_role: int = 2' in cfg); ck('required_roles','interactive,cpu,io' in cfg)
ck('ha_snapshot','def high_availability_snapshot' in ha); ck('candidate_not_redundancy','r.get("deployment_slot")=="stable"' in ha)
ck('draining_excluded','r.get("state")=="active"' in ha); ck('split_brain_detection','split_brain=len(active_beats) > 1' in ha)
ck('no_cascade','under_replication_blocks_individual_api_readiness": False' in ha)
ck('registry_non_authoritative','redis_registry_authoritative": False' in ha)
ck('physical_ha_disclaimer','physical_host_redundancy_requires_external_orchestrator_or_load_balancer' in ha)
ck('app_tier_scope','"ha_scope": "application_tier"' in ha and '"full_stack_ha_claimed": False' in ha)
ck('shared_storage_boundary','shared_evidence_storage_required_across_api_replicas' in ha and 'postgresql_failover_managed_by_mgc' in ha)
ck('operations_endpoint','@router.get("/high-availability")' in ops)
ck('operations_admin','def high_availability' in ops and '_admin(identity)' in ops[ops.index('def high_availability'):ops.index('def high_availability')+220])
ck('support_bundle','"high-availability.json"' in support); ck('ops_summary','"high_availability": high_availability' in support)
ck('api_healthcheck','/api/v1/health/ready' in compose and 'healthcheck:' in compose[compose.index('  api:'):compose.index('  worker:')])
for service in ('api-ha','worker-ha','worker-cpu-ha','worker-io-ha','beat-ha','frontend-ha'):
    ck('overlay_'+service, re.search(r'^  '+re.escape(service)+r':',overlay,re.M) is not None)
ck('ha_overlay_enables','HA_ENABLED: "true"' in overlay)
ck('ha_overlay_no_public_ports','ports:' not in overlay)
ck('ha_replicas_inherit_secure_base',all(f'  {name}:\n    extends:' in overlay for name in ('api-ha','worker-ha','worker-cpu-ha','worker-io-ha','beat-ha','frontend-ha')))
ck('gateway_two_api','API_UPSTREAM_PRIMARY' in overlay and 'API_UPSTREAM_SECONDARY' in overlay)
ck('gateway_passive_failover','proxy_next_upstream error timeout http_502 http_503 http_504;' in gw)
ck('no_non_idempotent_retry', all('non_idempotent' not in line for line in gw.splitlines() if line.strip().startswith('proxy_next_upstream ')))
ck('gateway_bounded_tries','proxy_next_upstream_tries 2;' in gw)
ck('scheduler_pg_lock','pg_try_advisory_lock' in beat and 'state="standby"' in beat)
ck('scheduler_lock_loss_fails_closed','_assert_lock_session(conn)' in beat and 'return 75' in beat)
ck('worker_late_ack','task_acks_late=True' in celery and 'task_reject_on_worker_lost=True' in celery)
ck('drill_confirmation','MGC_HA_DRILL_CONFIRM' in drill and 'YES' in drill)
ck('drill_api_loss','stop api' in drill and 'start api' in drill)
ck('drill_worker_loss','stop worker-cpu' in drill and 'start worker-cpu' in drill)
ck('drill_checks_snapshot','high_availability_snapshot' in drill)
ck('no_db_migration','ensure_v6318_schema' not in text('backend/app/db/migrations.py'))
failed=[n for n,ok in checks if not ok]
for n,ok in checks: print(('PASS' if ok else 'FAIL'),n)
print(f'SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS')
if failed: raise SystemExit(1)
