#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/runtime_lib.sh
runtime="$(select_runtime "$ROOT")"
vision="${MGC_CPU_VISION:-$(env_value MGC_CPU_VISION "$ROOT")}"; vision="${vision:-false}"; [[ "$runtime" == cpu ]] || vision=false
if [[ "$runtime" == cpu && "$vision" == true ]]; then has_cpu_vision_models "$ROOT" || { echo "ERROR: CPU Vision requested but CPU_VLM_MODEL_FILE/mmproj assets are missing." >&2; exit 2; }; fi
mapfile -t FILES < <(compose_args "$ROOT" "$runtime" "$vision")
COMPOSE=(docker compose "${FILES[@]}")
echo "== MGC v6.0.9 engineer-only air-gap acceptance (${runtime^^}) =="
"${COMPOSE[@]}" ps

echo "== API health from private container network =="
"${COMPOSE[@]}" exec -T api python - <<'PY'
import urllib.request
print(urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health/ready', timeout=5).read().decode())
PY

echo "== Local AI runtime =="
"${COMPOSE[@]}" exec -T api python - <<'PY'
import asyncio, json
from app.services.local_ai import local_ai_status
s=asyncio.run(local_ai_status()); print(json.dumps(s,ensure_ascii=False,indent=2))
if not s.get('ready'): raise SystemExit('FAIL: local AI is not ready')
PY

echo "== Host exposure =="
python - "$runtime" <<'PY'
import subprocess,json,sys
runtime=sys.argv[1]
files=['docker-compose.airgap.yml',f'docker-compose.{runtime}.yml','docker-compose.sso.yml']
cmd=['docker','compose']
for f in files: cmd += ['-f',f]
out=subprocess.check_output(cmd+['ps','--format','json'],text=True)
for line in out.splitlines():
    if not line.strip(): continue
    row=json.loads(line); name=row.get('Service') or row.get('Name',''); pubs=row.get('Publishers') or []
    if name in {'api','frontend','gateway','model-server','vision-server','postgres','qdrant','redis','neo4j','minio'} and pubs:
        raise SystemExit(f'FAIL: {name} unexpectedly publishes host ports: {pubs}')
print('PASS: no direct application/data/model host ports')
PY

echo "== Engineer-only backend config =="
grep -Eq '^AUTH_MODE=oidc$' .env || { echo 'FAIL: AUTH_MODE must be oidc'; exit 1; }
grep -Eq '^ENGINEER_ONLY_ACCESS=true$' .env || { echo 'FAIL: ENGINEER_ONLY_ACCESS must be true'; exit 1; }
if grep -Eq '^ALLOW_API_KEY_AUTH_IN_PROD=true$' .env; then echo 'FAIL: API-key production bypass is enabled'; exit 1; fi

echo "== Static security =="
python scripts/docker_security_preflight.py
python scripts/compose_security_preflight.py
python scripts/api_access_preflight.py

echo "PASS: runtime/security checks complete. Complete one allowed engineer login and one denied non-engineer login before production sign-off."
