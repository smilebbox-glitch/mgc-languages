from pathlib import Path
import sys, yaml
root=Path(__file__).resolve().parents[1]
compose=root/'docker-compose.yml'
data=yaml.safe_load(compose.read_text())
errors=[]
expected={
 'api': ('backend','Dockerfile'),
 'worker': ('backend','Dockerfile'),
 'frontend': ('frontend','Dockerfile'),
 'gateway': ('.','ops/gateway/Dockerfile'),
}
for svc,(ctx,df) in expected.items():
    build=(data.get('services',{}).get(svc,{}) or {}).get('build')
    if not build:
        errors.append(f'{svc}: missing build section'); continue
    if isinstance(build,str): actual_ctx=build; actual_df='Dockerfile'
    else: actual_ctx=build.get('context'); actual_df=build.get('dockerfile','Dockerfile')
    context_path=(root/actual_ctx).resolve()
    dockerfile_path=(context_path/actual_df).resolve()
    if not context_path.exists(): errors.append(f'{svc}: build context missing: {context_path}')
    if not dockerfile_path.exists(): errors.append(f'{svc}: Dockerfile missing: {dockerfile_path}')
# Plain build must not require a runtime secret .env file.
compose_text=compose.read_text()
if 'env_file: .env' in compose_text: errors.append('docker-compose.yml requires .env during build; use optional env_file mapping')
# Critical files Dockerfiles COPY from their context.
for rel in ['backend/requirements.txt','backend/requirements-core.txt','backend/requirements-ai.txt','backend/requirements-advanced.txt','backend/app','frontend/package.json','frontend/src','ops/gateway/nginx.conf','ops/gateway/templates/default.conf.template']:
    if not (root/rel).exists(): errors.append(f'missing build input: {rel}')
if errors:
    print('BUILD PREFLIGHT: FAIL')
    for e in errors: print(' -',e)
    sys.exit(1)
print('BUILD PREFLIGHT: PASS')
print('Plain command supported: docker compose build')
