from __future__ import annotations
import json, os, sys, urllib.request

def env(name, default=''): return os.getenv(name, default).strip()
errors=[]; warnings=[]
if env('AUTH_MODE','local').lower() != 'oidc':
    warnings.append('AUTH_MODE is not oidc; this check validates configuration only')
for name in ('OIDC_DISCOVERY_URL','OIDC_CLIENT_ID','OIDC_CLIENT_SECRET','OIDC_STATE_SECRET'):
    if not env(name): errors.append(f'{name} is required')
if not env('OIDC_USERNAME_CLAIM'): errors.append('OIDC_USERNAME_CLAIM is required')
if not env('OIDC_DEPARTMENT_CLAIM'):
    warnings.append('OIDC_DEPARTMENT_CLAIM is empty; Manager department scoping cannot be populated from IdP')
if not any(env(x) for x in ('OIDC_ADMIN_GROUP','OIDC_EDITOR_GROUP','OIDC_MANAGER_GROUP')):
    warnings.append('No OIDC role groups are configured')

verify=env('OIDC_VERIFY_DISCOVERY','false').lower() in {'1','true','yes','on'}
if verify and not errors:
    try:
        with urllib.request.urlopen(env('OIDC_DISCOVERY_URL'), timeout=10) as r:
            doc=json.load(r)
        for key in ('authorization_endpoint','token_endpoint','jwks_uri'):
            if not doc.get(key): errors.append(f'discovery metadata lacks {key}')
        print('Discovery issuer:',doc.get('issuer','<missing>'))
    except Exception as exc:
        errors.append(f'OIDC discovery fetch failed: {exc}')

for w in warnings: print('WARN:',w)
for e in errors: print('ERROR:',e)
if errors: sys.exit(2)
print('PASS: OIDC configuration shape is acceptable')
