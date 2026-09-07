#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,yaml,re
ROOT=Path(__file__).resolve().parents[1]
checks=[]; errors=[]
def ck(ok,name,detail):
    checks.append((bool(ok),name,detail))
    if not ok: errors.append(f'{name}: {detail}')
sec=(ROOT/'backend/app/core/security.py').read_text()
cfg=(ROOT/'backend/app/core/config.py').read_text()
routes='\n'.join(p.read_text() for p in (ROOT/'backend/app/api').rglob('*.py'))
overlay=yaml.safe_load((ROOT/'docker-compose.enterprise-security.yml').read_text())
edge=(ROOT/'ops/enterprise-edge/nginx.conf').read_text()
ck('Invalid OIDC token: {exc}' not in sec,'oidc.no-error-disclosure','OIDC parser/JWKS errors are not returned to callers')
ck('oidc_allowed_algorithm_set' in sec and 'startswith("HS")' in sec,'oidc.asymmetric-allowlist','symmetric/none algorithms rejected')
ck('allow_trusted_headers_in_prod' in sec and 'trusted_proxy_secret' in sec,'trusted-header.fail-closed','production trusted headers require explicit opt-in + proxy secret')
ck('oidc_clock_skew_seconds' in cfg,'oidc.bounded-skew','clock skew is configurable and bounded')
ck('allow_methods=cfg.cors_method_list' in (ROOT/'backend/app/main.py').read_text() and 'allow_headers=cfg.cors_header_list' in (ROOT/'backend/app/main.py').read_text(),'cors.explicit-methods-headers','CORS methods/headers are explicit, not wildcard')
ck('/security/posture' in routes and '/security/audit/export' in routes and '/security/audit/retention' in routes,'audit.admin-api','security posture/export/retention endpoints exist')
services=overlay['services']
for name in ['schema-migrate','enterprise-edge']:
    svc=services[name]; ck('no-new-privileges:true' in (svc.get('security_opt') or []),f'{name}.nnp','no privilege escalation'); ck('ALL' in (svc.get('cap_drop') or []),f'{name}.caps','all Linux capabilities dropped'); ck(svc.get('read_only') is True,f'{name}.readonly','read-only root filesystem')
ck(str(services['api']['environment'].get('AUTO_MIGRATE_SCHEMA')).lower()=='false','least-privilege.api-no-migrate','runtime API does not perform schema DDL')
ck(str(services.get('beat',{}).get('environment',{}).get('AUTO_MIGRATE_SCHEMA')).lower()=='false','least-privilege.beat-no-migrate','scheduler does not perform schema DDL')
ck('MGC_MIGRATION_DATABASE_URL' in (ROOT/'docker-compose.enterprise-security.yml').read_text(),'least-privilege.migration-role','one-shot migration connection is separate')
ck('ssl_protocols TLSv1.2 TLSv1.3' in edge,'tls.protocols','TLS 1.2/1.3 only')
ck('ssl_verify_client on' in edge and 'ssl_client_certificate' in edge,'mtls.integration-edge','machine webhook edge requires client certificate')
ck('Strict-Transport-Security' in edge,'tls.hsts','HSTS enabled at enterprise edge')
ck((ROOT/'scripts/generate_sbom.py').exists(),'supply-chain.sbom','offline SBOM generator included')
ck((ROOT/'scripts/secret_scan.py').exists(),'supply-chain.secrets','deterministic source secret scanner included')
ck((ROOT/'scripts/vulnerability_scan.sh').exists(),'supply-chain.cve-hook','approved build-host CVE scanner hook included')
ck('npm ci' in (ROOT/'frontend/Dockerfile').read_text(),'supply-chain.npm-ci','frontend build uses npm ci when an approved lockfile is present')
ck(':latest' not in (ROOT/'.env.enterprise.example').read_text(),'supply-chain.enterprise-no-latest','enterprise deployment template forbids floating latest tags')
print('Enterprise security preflight')
for ok,n,d in checks: print(f"{'PASS' if ok else 'FAIL':4} {n:38} — {d}")
if errors: raise SystemExit('\n'.join(errors))
print(f'PASS: {len(checks)} checks, 0 failures')
