from __future__ import annotations
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
load=lambda n: yaml.safe_load((ROOT/n).read_text())
airg=load('docker-compose.airgap.yml'); gpu=load('docker-compose.gpu.yml'); cpu=load('docker-compose.cpu.yml'); cpuv=load('docker-compose.cpu-vision.yml'); sso=load('docker-compose.sso.yml'); pilot=load('docker-compose.pilot.yml'); webh=load('docker-compose.webhooks.yml'); ent=load('docker-compose.enterprise-security.yml'); pitr=load('docker-compose.pitr.yml')
checks=[]; errors=[]
def ck(ok,name,detail):
    checks.append((bool(ok),name,detail))
    if not ok: errors.append(f'{name}: {detail}')
def hardening(service,name):
    sec=set(service.get('security_opt') or []); caps=set(service.get('cap_drop') or [])
    ck('no-new-privileges:true' in sec,f'{name}.no-new-privileges','disable privilege escalation')
    ck('ALL' in caps,f'{name}.cap-drop','drop Linux capabilities')
    ck(service.get('read_only') is True,f'{name}.read-only','read-only root filesystem')
    ck(bool(service.get('tmpfs')),f'{name}.tmpfs','writable runtime paths use tmpfs')
services=airg['services']
for name in ['api','worker','frontend','gateway']: hardening(services[name],name)
hardening(cpu['services']['model-server'],'cpu-model-server')
hardening(cpuv['services']['vision-server'],'cpu-vision-server')
hardening(sso['services']['auth-proxy'],'auth-proxy'); hardening(webh['services']['webhook-edge'],'webhook-edge')
# no application/data/model service may be host-published in production layers
for source,label in [(airg,'base'),(gpu,'gpu'),(cpu,'cpu'),(cpuv,'cpu-vision')]:
    for name,svc in (source.get('services') or {}).items():
        if name != 'auth-proxy': ck(not svc.get('ports'),f'{label}.{name}.not-host-published','production service must not publish host ports')
for source,label in [(airg,'base'),(gpu,'gpu'),(cpu,'cpu'),(cpuv,'cpu-vision')]:
    for name,svc in (source.get('services') or {}).items():
        if 'image' in svc: ck(svc.get('pull_policy')=='never',f'{label}.{name}.pull-policy','air-gap service uses pull_policy: never')
for fn in ['docker-compose.airgap.yml','docker-compose.gpu.yml','docker-compose.cpu.yml','docker-compose.cpu-vision.yml']:
    ck(':latest' not in (ROOT/fn).read_text().lower(),f'{fn}.no-latest','no floating latest image tags')
ck('model-server' not in services,'base.runtime-separated','base Compose must not hard-code GPU or CPU model server')
ck('devices' in (((gpu['services']['model-server'].get('deploy') or {}).get('resources') or {}).get('reservations') or {}),'gpu.requires-device','GPU overlay reserves NVIDIA device')
cpu_cmd=' '.join(str(x) for x in cpu['services']['model-server'].get('command') or [])
ck('--gpu-layers 0' in cpu_cmd,'cpu.no-gpu-layers','CPU profile explicitly disables GPU offload')
ck('--no-webui' in cpu_cmd,'cpu.no-model-webui','llama.cpp WebUI is disabled')
ck('--api-key' in cpu_cmd,'cpu.model-api-key','CPU model server requires API key')
ck(bool(sso['services']['auth-proxy'].get('ports')),'sso.only-public-entry','SSO proxy is intended production host entry')
ck(not (sso['services'].get('gateway') or {}).get('ports'),'sso.no-gateway-bypass','SSO overlay must not expose gateway')
api_env=sso['services']['api'].get('environment') or {}
ck(str(api_env.get('AUTH_MODE','')).lower()=='oidc','sso.backend-validates-oidc','backend validates OIDC')
ck(str(api_env.get('ENGINEER_ONLY_ACCESS','')).lower()=='true','sso.engineer-only','engineer-only authorization enabled')
proxy_cmd=' '.join(str(x) for x in sso['services']['auth-proxy'].get('command') or [])
ck('--allowed-group=' in proxy_cmd,'sso.group-gate','edge proxy requires engineering group')
ck('--pass-access-token=true' in proxy_cmd,'sso.pass-token','access token reaches backend validation layer')
ck(bool((pilot['services'].get('gateway') or {}).get('ports')),'pilot.explicit-port','direct gateway exists only in explicit pilot override')
security=(ROOT/'backend/app/core/security.py').read_text()
ck('allow_api_key_auth_in_prod' in security and 'API-key human access is disabled in production' in security,'backend.no-shared-key-prod','production rejects shared API-key human access')
stack=(ROOT/'scripts/stack.sh').read_text(); runtime=(ROOT/'scripts/runtime_lib.sh').read_text(); make=(ROOT/'Makefile').read_text()
ck('select_runtime' in stack and 'docker-compose.${runtime}.yml' in runtime,'launch.runtime-selector','canonical launch selects CPU/GPU overlay')
ck('MGC_RUNTIME=cpu ./scripts/stack.sh up -d' in make,'launch.explicit-cpu','Makefile exposes explicit CPU launch')
ck('MGC_RUNTIME=gpu ./scripts/stack.sh up -d' in make,'launch.explicit-gpu','Makefile exposes explicit GPU launch')
worker_hc=' '.join(str(x) for x in ((services['worker'].get('healthcheck') or {}).get('test') or []))
ck('app.workers.healthcheck' in worker_hc,'worker.healthcheck','Celery worker uses worker-specific healthcheck')

# v6.0.5 enterprise edge / least-privilege deployment
ent_services=ent['services']
hardening(ent_services['schema-migrate'],'schema-migrate')
hardening(ent_services['enterprise-edge'],'enterprise-edge')
ck(str((ent_services['api'].get('environment') or {}).get('AUTO_MIGRATE_SCHEMA','')).lower()=='false','enterprise.api-no-ddl','runtime API does not perform schema DDL')
ck(str((ent_services['worker'].get('environment') or {}).get('AUTO_MIGRATE_SCHEMA','')).lower()=='false','enterprise.worker-no-ddl','runtime worker does not perform schema DDL')
enterprise_text=(ROOT/'docker-compose.enterprise-security.yml').read_text()
ck('MGC_RUNTIME_DATABASE_URL' in enterprise_text and 'MGC_MIGRATION_DATABASE_URL' in enterprise_text,'enterprise.db-role-split','runtime and migration database identities are separate')
edge_nginx=(ROOT/'ops/enterprise-edge/nginx.conf').read_text()
ck('ssl_protocols TLSv1.2 TLSv1.3' in edge_nginx,'enterprise.tls12-13','enterprise edge allows only TLS 1.2/1.3')
ck('ssl_verify_client on' in edge_nginx,'enterprise.mtls','integration edge requires client certificates')
ck('Strict-Transport-Security' in edge_nginx,'enterprise.hsts','enterprise browser edge emits HSTS')


# v6.3.14 optional PostgreSQL PITR overlay: no public exposure and no network exfiltration command.
pitr_pg=pitr['services']['postgres']; pitr_text=(ROOT/'docker-compose.pitr.yml').read_text()
ck(not pitr_pg.get('ports'),'pitr.no-public-port','PITR overlay does not publish PostgreSQL')
ck('MGC_PITR_ARCHIVE_PATH:?' in pitr_text,'pitr.explicit-archive-target','PITR requires an explicit archive target')
ck('archive_mode=on' in pitr_text and 'wal_level=replica' in pitr_text,'pitr.wal-settings','PITR overlay enables WAL archiving posture')
ck('curl ' not in pitr_text and 'wget ' not in pitr_text and 'http://' not in pitr_text and 'https://' not in pitr_text,'pitr.no-network-archive-command','default archive command copies only to mounted protected storage')


# v6.3.34 per-node multi-host overlay: only gateway may publish, and only to explicit bind IP.
mh=load('docker-compose.multihost.yml'); mh_text=(ROOT/'docker-compose.multihost.yml').read_text()
for name,svc in (mh.get('services') or {}).items():
    if name != 'gateway': ck(not svc.get('ports'),f'multihost.{name}.not-host-published','multi-host app/data service must not publish host ports')
ck(bool((mh['services'].get('gateway') or {}).get('ports')),'multihost.gateway-explicit-edge','per-node gateway is the only published edge')
ck('MGC_NODE_BIND_IP:?' in mh_text and '0.0.0.0' not in mh_text,'multihost.explicit-bind','multi-host edge requires explicit non-wildcard bind')
ck('DATABASE_URL:?' in mh_text and 'REDIS_URL:?' in mh_text,'multihost.shared-authority-endpoints','multi-host mode requires explicit shared DB/Redis endpoints')
ck('DATABASE_HA_ENABLED: "true"' in mh_text and 'EVIDENCE_HA_ENABLED: "true"' in mh_text,'multihost.authoritative-fencing','multi-host mode enables authoritative DB/evidence fencing')

api_docker=(ROOT/'backend/Dockerfile').read_text()
ck('/api/v1/health/ready' in api_docker,'api.readiness-healthcheck','API image healthcheck uses readiness, not liveness')
print('Compose/access/runtime security static preflight')
for ok,name,detail in checks: print(f"{'PASS' if ok else 'FAIL':4} {name:40} — {detail}")
if errors: raise SystemExit('\n'.join(errors))
print(f'PASS: {len(checks)} checks, 0 failures')
