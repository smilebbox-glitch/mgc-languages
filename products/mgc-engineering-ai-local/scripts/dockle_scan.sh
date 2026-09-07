#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="${DOCKLE_REPORT_DIR:-$ROOT/security-reports/dockle}"
mkdir -p "$OUT"
MGC_VERSION="${MGC_VERSION:-$(PYTHONPATH=backend python -c 'from app.core.runtime_contract import APP_VERSION; print(APP_VERSION)')}"
export MGC_VERSION

IMAGES=(
  "${MGC_API_IMAGE:-mgc-engineering-ai-api:${MGC_VERSION}-local}"
  "${MGC_FRONTEND_IMAGE:-mgc-engineering-ai-frontend:${MGC_VERSION}-local}"
  "${MGC_GATEWAY_IMAGE:-mgc-engineering-ai-gateway:${MGC_VERSION}-local}"
  "${MGC_WEBHOOK_IMAGE:-mgc-engineering-ai-webhook-edge:${MGC_VERSION}-local}"
)
if [[ "${1:-}" == "--all" ]]; then
  [[ -n "${LLAMA_CPP_IMAGE:-}" ]] && IMAGES+=("$LLAMA_CPP_IMAGE")
  [[ -n "${VLLM_IMAGE:-}" ]] && IMAGES+=("$VLLM_IMAGE")
  IMAGES+=(
    "${POSTGRES_IMAGE:-postgres:16}"
    "${QDRANT_IMAGE:-qdrant/qdrant:REPLACE_WITH_APPROVED_VERSION}"
    "${REDIS_IMAGE:-redis:7-alpine}"
    "${NEO4J_IMAGE:-neo4j:5-community}"
    "${MINIO_IMAGE:-minio/minio:REPLACE_WITH_APPROVED_RELEASE}"
  )
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is required to scan built images." >&2
  exit 2
fi
for image in "${IMAGES[@]}"; do docker image inspect "$image" >/dev/null; done

run_dockle() {
  local image="$1" output="$2"
  if command -v dockle >/dev/null 2>&1; then
    dockle --exit-code 1 --exit-level fatal -f json -o "$output" "$image"
  else
    local scanner="${DOCKLE_IMAGE:-}"
    if [[ -z "$scanner" ]]; then
      echo "ERROR: dockle binary not found. Set DOCKLE_IMAGE to an approved pinned Dockle image." >&2
      return 2
    fi
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$OUT:/reports" "$scanner" \
      --exit-code 1 --exit-level fatal -f json -o "/reports/$(basename "$output")" "$image"
  fi
}

status=0
for image in "${IMAGES[@]}"; do
  safe="$(echo "$image" | tr '/:@' '____')"
  echo "Dockle: $image"
  if ! run_dockle "$image" "$OUT/$safe.json"; then
    status=1
  fi
done

python - "$OUT" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
rows=[]
for p in sorted(root.glob('*.json')):
    try:
        data=json.loads(p.read_text())
        s=data.get('summary',{})
        rows.append((p.name,s.get('fatal',0),s.get('warn',0),s.get('info',0),s.get('pass',0)))
    except Exception:
        rows.append((p.name,'?','?','?','?'))
print('REPORT'.ljust(64),'FATAL WARN INFO PASS')
for r in rows:
    print(r[0].ljust(64),*r[1:])
PY
exit "$status"
