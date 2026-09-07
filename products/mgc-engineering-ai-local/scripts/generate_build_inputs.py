#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=[
 'frontend/package.json','frontend/package-lock.json','frontend/Dockerfile','frontend/.dockerignore',
 'backend/requirements-core.txt','backend/requirements-ai.txt','backend/requirements-advanced.txt','backend/requirements.txt',
 'backend/Dockerfile','backend/verify_os_package_bundle.py',
 'ops/gateway/Dockerfile','ops/webhook-gateway/Dockerfile','ops/enterprise-edge/Dockerfile','ops/mock-integrations/Dockerfile',
 'docker-compose.yml','docker-compose.airgap.yml','docker-compose.build.yml','docker-compose.connected.yml','docker-compose.reproducible.yml','docker-compose.pitr.yml',
 'scripts/reproducible_build.sh','scripts/docker_build.sh','scripts/prepare_airgap_bundle.sh','scripts/prepare_python_lock.py',
 'scripts/prepare_frontend_lock.sh','scripts/prepare_os_package_bundle.sh','scripts/verify_os_package_install.sh','scripts/resolve_container_digests.py',
 'scripts/generate_build_inputs.py','scripts/supply_chain_preflight.py','scripts/supply_chain_v6_3_12_preflight.py',
 'scripts/backup_core.sh','scripts/restore_core.sh','scripts/backup_manifest.py','scripts/dr_consistency_compare.py','scripts/dr_consistency_preflight.py',
 'scripts/generate_build_attestation.py','scripts/verify_build_attestation.py','scripts/dependency_lock_preflight.py','scripts/validate_airgap_image_pins.py',
 'scripts/rolling_upgrade.sh','scripts/rolling_upgrade_preflight.py',
 'docker-compose.bluegreen.yml','docker-compose.ha.yml','ops/gateway/templates/default.conf.template','ops/gateway/templates/ha.conf.template',
 'scripts/blue_green_cutover.sh','scripts/blue_green_rollback.sh','scripts/blue_green_finalize.sh',
 'scripts/blue_green_cutover_preflight.py','scripts/cutover_contract_check.py',
 'scripts/ha_failover_preflight.py','scripts/ha_failover_drill.sh',
 'docker-compose.authoritative-ha.yml','scripts/authoritative_ha_runtime_check.py',
 'scripts/authoritative_recovery_point.py','scripts/db_evidence_ha_preflight.py','scripts/evidence_ha_marker.py',
 'docker-compose.multihost.yml','ops/external-lb/haproxy.cfg.example',
 'ops/multihost/topology.15.example.json','ops/multihost/topology.30.example.json','ops/multihost/topology.100.example.json',
 'scripts/topology_certify.py','scripts/multihost_deployment_guard.py','scripts/multihost_topology_preflight.py','scripts/multihost_failover_drill.sh',
 'backend/app/core/production_certification.py','backend/app/core/db_pool_admission.py','backend/app/core/load_certification.py',
 'scripts/production_certify.py','scripts/production_deployment_guard.py','scripts/production_certification_preflight.py',
 'scripts/production_load_certify.py','scripts/production_load_certification_preflight.py','ops/certification/load-plan.v1.json',
 'ops/certification/evidence.15.example.json','ops/certification/evidence.30.example.json','ops/certification/evidence.100.example.json',
 'backend/app/core/release_acceptance.py','scripts/release_acceptance_pipeline.py','scripts/release_acceptance_preflight.py',
 'scripts/promote_acceptance_baseline.py','scripts/verify_acceptance_chain.py',
 'backend/app/core/release_provenance.py','backend/app/core/release_provenance_governance.py','scripts/release_provenance_registry.py','scripts/release_provenance_preflight.py','scripts/external_trust_retention_preflight.py',
 'mgcctl','scripts/mgcctl.py','scripts/operations_consolidation_preflight.py','backend/tests/test_v6326_operations_consolidation.py',
 'backend/app/services/integration_certification.py','backend/tests/test_v6327_real_integration_certification.py','backend/tests/test_v6328_integration_runtime_assurance.py',
 'scripts/integration_certify.py','scripts/integration_contract_suite.py','scripts/integration_certification_preflight.py','scripts/integration_runtime_assurance_preflight.py',
 'backend/app/core/target_host_assurance.py','backend/tests/test_v6329_target_host_assurance.py','scripts/target_host_probe.py','scripts/target_host_certify.py','scripts/target_host_deployment_guard.py','scripts/target_host_assurance_preflight.py',
 'backend/app/core/incident_evidence.py','backend/tests/test_v6330_production_observability_incident_evidence.py','scripts/incident_evidence_preflight.py','PRODUCTION_OBSERVABILITY_INCIDENT_EVIDENCE_v6.3.30.md','docs/PRODUCTION_OBSERVABILITY_INCIDENT_EVIDENCE_v6.3.30.md',
 'backend/app/core/resilience_drill.py','backend/tests/test_v6331_resilience_drill_orchestration.py','scripts/resilience_drill.py','scripts/resilience_drill_preflight.py','RESILIENCE_DRILL_ORCHESTRATION_v6.3.31.md','docs/RESILIENCE_DRILL_ORCHESTRATION_v6.3.31.md',
 'backend/app/core/resilience_certification.py','backend/tests/test_v6332_resilience_certification_recovery_baselines.py','scripts/resilience_certify.py','scripts/resilience_release_guard.py','scripts/resilience_certification_preflight.py','RESILIENCE_CERTIFICATION_RECOVERY_BASELINES_v6.3.34.md','docs/RESILIENCE_CERTIFICATION_RECOVERY_BASELINES_v6.3.34.md',
 'backend/app/services/project_workspace.py','backend/tests/test_v6333_pilot_readiness_ux_simplification.py','scripts/pilot_readiness_preflight.py','frontend/src/main.tsx','frontend/src/styles.css','PILOT_READINESS_UX_SIMPLIFICATION_v6.3.34.md','docs/PILOT_READINESS_UX_SIMPLIFICATION_v6.3.34.md',
 'backend/app/core/vehicle_applicability.py','backend/tests/test_v6334_multi_vehicle_applicability.py','scripts/multi_vehicle_applicability_preflight.py','MULTI_VEHICLE_PRODUCT_APPLICABILITY_v6.3.34.md','docs/MULTI_VEHICLE_PRODUCT_APPLICABILITY_v6.3.34.md',
 'ops/certification/target-host/evidence.node-a.example.json','ops/certification/target-host/evidence.node-b.example.json','TARGET_HOST_DEPLOYMENT_ASSURANCE_v6.3.34.md','docs/TARGET_HOST_DEPLOYMENT_ASSURANCE_v6.3.34.md',
 'ops/integrations/README.md','ops/integrations/contracts/plm.example.json','ops/integrations/contracts/pdm.example.json','ops/integrations/contracts/erp.example.json','ops/integrations/contracts/mes.example.json','ops/integrations/contracts/qms.example.json','ops/integrations/plm.simulator.json',
 'Makefile','.env.example','EXTERNAL_TRUST_RETENTION_v6.3.25.md','OPERATIONS_CONSOLIDATION_v6.3.26.md','REAL_INTEGRATION_CERTIFICATION_v6.3.27.md','INTEGRATION_RUNTIME_ASSURANCE_v6.3.28.md','RELEASE_NOTES_v6.3.34_RU.md','VERIFICATION_v6.3.34.md','docs/API_BOUNDED_CONTEXTS_v6.3.34.md',
 'supply-chain/SUPPLY_CHAIN_POLICY.json'
]
IMAGE_KEYS=['PYTHON_BASE_IMAGE','NODE_BASE_IMAGE','NGINX_BASE_IMAGE','POSTGRES_IMAGE','REDIS_IMAGE','QDRANT_IMAGE','NEO4J_IMAGE','MINIO_IMAGE','VLLM_IMAGE','LLAMA_CPP_IMAGE','OAUTH2_PROXY_IMAGE','PROMETHEUS_IMAGE','GRAFANA_IMAGE','JAEGER_IMAGE']

def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()

def load_env(path:Path)->dict[str,str]:
    out={}
    if not path.exists(): return out
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--env',default=''); args=ap.parse_args()
    rows=[]
    for rel in FILES:
        p=ROOT/rel
        rows.append({'path':rel,'present':p.exists(),'sha256':sha(p) if p.exists() else None,'bytes':p.stat().st_size if p.exists() else None})
    for profile in ('core','ai','advanced'):
        for rel in [f'backend/locks/requirements-{profile}.lock.txt',f'backend/wheelhouse/{profile}/WHEELHOUSE_MANIFEST.json']:
            p=ROOT/rel; rows.append({'path':rel,'present':p.exists(),'sha256':sha(p) if p.exists() else None,'bytes':p.stat().st_size if p.exists() else None})
    os_root=ROOT/'backend/os-packages/runtime'
    for p in sorted(os_root.glob('*')) if os_root.exists() else []:
        if p.is_file() and p.name != '.gitkeep':
            rel=str(p.relative_to(ROOT)); rows.append({'path':rel,'present':True,'sha256':sha(p),'bytes':p.stat().st_size})
    env_values=load_env(ROOT/args.env) if args.env else {}
    immutable_images={k:(os.getenv(k) or env_values.get(k,'')) for k in IMAGE_KEYS}
    out={'schema':'mgc.build-inputs.v2','release':'6.3.34','files':rows,'immutable_images':immutable_images}
    target=ROOT/'supply-chain/BUILD_INPUTS.json'
    target.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (ROOT/'supply-chain/BUILD_INPUTS.sha256').write_text(digest+'  BUILD_INPUTS.json\n')
    print('WROTE supply-chain/BUILD_INPUTS.json',len(rows),'file inputs',len(immutable_images),'image refs',digest)
if __name__=='__main__': main()
