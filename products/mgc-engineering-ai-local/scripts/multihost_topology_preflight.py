#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def text(p): return (ROOT/p).read_text(encoding='utf-8')
def ck(name, ok): checks.append((name,bool(ok))); print(('PASS' if ok else 'FAIL')+': '+name)
rt=text('backend/app/core/runtime_contract.py'); cfg=text('backend/app/core/config.py'); dep=text('backend/app/core/deployment_safety.py')
topo=text('backend/app/core/multi_host_topology.py'); health=text('backend/app/api/health_routes.py'); ops=text('backend/app/api/operations_routes.py')
support=text('backend/app/services/production_support.py'); compose=text('docker-compose.multihost.yml'); lb=text('ops/external-lb/haproxy.cfg.example')
cert=text('scripts/topology_certify.py'); guard=text('scripts/multihost_deployment_guard.py'); api_access=text('scripts/api_access_preflight.py')
ck('app_version_6320','APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
for key in ('multi_host_topology_enabled','topology_node_id','topology_failure_domain','topology_min_failure_domains','topology_external_lb_health_path'):
    ck('config_'+key, key in cfg)
ck('heartbeat_node_id','"topology_node_id"' in dep)
ck('heartbeat_failure_domain','"topology_failure_domain"' in dep)
ck('topology_snapshot','def multi_host_topology_snapshot' in topo)
ck('anti_affinity_policy','anti_affinity_required_across_failure_domains' in topo)
ck('registry_not_truth','registry_is_ephemeral' in topo)
ck('underreplication_no_cascade','under_replication_blocks_individual_api_readiness' in topo)
ck('lb_health_route','@router.get("/health/lb")' in health and 'mgc-external-lb-v1' in health)
ck('lb_route_sanitized','dependency' not in health[health.index('@router.get("/health/lb")'):])
ck('lb_route_exempt_explicit','("health_routes.py", "/health/lb")' in api_access)
ck('operations_endpoint','@router.get("/multi-host-topology")' in ops)
ck('support_bundle','"multi-host-topology.json"' in support)
ck('compose_overlay', 'MGC_NODE_ID:?' in compose and 'MGC_FAILURE_DOMAIN:?' in compose)
ck('compose_external_db_required','DATABASE_URL: ${DATABASE_URL:?' in compose)
ck('compose_shared_redis_required','REDIS_URL: ${REDIS_URL:?' in compose)
ck('compose_authority_fencing','DATABASE_HA_ENABLED: "true"' in compose and 'EVIDENCE_HA_ENABLED: "true"' in compose)
ck('compose_explicit_edge_bind','MGC_NODE_BIND_IP:?' in compose and '0.0.0.0' not in compose)
ck('lb_uses_health_contract','option httpchk GET /api/v1/health/lb' in lb)
ck('lb_no_request_retry','retries 0' in lb and 'retry-on' not in '\n'.join(x for x in lb.splitlines() if not x.lstrip().startswith('#')) and 'redispatch' not in '\n'.join(x for x in lb.splitlines() if not x.lstrip().startswith('#')))
ck('topology_profiles_15_30_100', all(f'"{x}"' in cert for x in ('15','30','100')))
ck('certification_not_performance','performance_certified":False' in cert and 'production_authorized":False' in cert)
ck('deployment_guard_fail_closed','status' in guard and 'HEALTHY' in guard and 'failed closed' in guard)
for profile in ('15','30','100'):
    inv=ROOT/f'ops/multihost/topology.{profile}.example.json'
    r=subprocess.run([sys.executable,str(ROOT/'scripts/topology_certify.py'),'--inventory',str(inv),'--profile',profile],cwd=ROOT,capture_output=True,text=True)
    ck('example_inventory_profile_'+profile,r.returncode==0)
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('v6.3.34 multi-host topology preflight failed: '+', '.join(failed))
print(f'PASS: v6.3.34 Multi-host Production Topology preflight ({len(checks)}/{len(checks)})')
