#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/runtime_lib.sh
runtime="$(select_runtime "$ROOT")"
vision="${MGC_CPU_VISION:-$(env_value MGC_CPU_VISION "$ROOT")}"; vision="${vision:-false}"
[[ "$runtime" == cpu ]] || vision=false
if [[ "$runtime" == cpu && "$vision" == true ]]; then has_cpu_vision_models "$ROOT" || { echo "ERROR: CPU Vision requested but CPU_VLM_MODEL_FILE/mmproj assets are missing." >&2; exit 2; }; fi
BUNDLE="${1:-$ROOT/dist/mgc-airgap-bundle-${runtime}}"
mkdir -p "$BUNDLE"

echo "Preparing air-gap bundle for runtime: ${runtime^^}"
if [[ "$runtime" == cpu ]]; then
  python scripts/verify_cpu_model.py models/cpu
else
  python scripts/verify_model_manifest.py models
fi
# Embeddings/reranker/docling are shared with both modes. If the main manifest is present, verify it too.
if [[ -f models/MODEL_MANIFEST.json ]]; then python scripts/verify_model_manifest.py models; fi
python scripts/validate_airgap_image_pins.py --runtime "$runtime"
if [[ "${MGC_REQUIRE_REPRODUCIBLE_BUILD:-false}" == "true" ]]; then
  python scripts/supply_chain_preflight.py --strict --env "${MGC_REPRODUCIBLE_ENV_FILE:-.env.reproducible}"
  ./scripts/reproducible_build.sh
else
  python scripts/supply_chain_preflight.py
  ./scripts/docker_build.sh
fi

mapfile -t FILES < <(compose_args "$ROOT" "$runtime" "$vision")
mapfile -t IMAGES < <(docker compose --env-file .env "${FILES[@]}" -f docker-compose.build.yml config --images | sort -u)
if [[ ${#IMAGES[@]} -eq 0 ]]; then echo "ERROR: no Docker images resolved" >&2; exit 1; fi
for image in "${IMAGES[@]}"; do docker image inspect "$image" >/dev/null 2>&1 || docker pull "$image"; done

docker save -o "$BUNDLE/docker-images.tar" "${IMAGES[@]}"
: > "$BUNDLE/docker-images.manifest"
for image in "${IMAGES[@]}"; do docker image inspect --format "{{.RepoTags}} {{.Id}}" "$image" >> "$BUNDLE/docker-images.manifest"; done
rsync -a --delete --exclude '.git' --exclude 'dist' --exclude '.env' --exclude 'models' "$ROOT/" "$BUNDLE/project/"
rm -rf "$BUNDLE/models"; mkdir -p "$BUNDLE/models"
for dir in embeddings reranker docling; do [[ -d "models/$dir" ]] && cp -a "models/$dir" "$BUNDLE/models/"; done
if [[ -f models/MODEL_MANIFEST.json ]]; then
  if [[ "$runtime" == cpu ]]; then
    python - "$BUNDLE/models/MODEL_MANIFEST.json" <<'PYFILTER'
import json,sys
from pathlib import Path
src=Path('models/MODEL_MANIFEST.json'); data=json.loads(src.read_text(encoding='utf-8'))
data['models'].pop('generative',None)
Path(sys.argv[1]).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
PYFILTER
  else
    cp models/MODEL_MANIFEST.json "$BUNDLE/models/"
  fi
fi
if [[ "$runtime" == cpu ]]; then
  cp -a models/cpu "$BUNDLE/models/"
  [[ "$vision" == true ]] && cp -a models/cpu-vision "$BUNDLE/models/"
else
  cp -a models/generative "$BUNDLE/models/"
fi
sha256sum "$BUNDLE/docker-images.tar" > "$BUNDLE/docker-images.tar.sha256"
( cd "$BUNDLE"; find models -type f -print0 | sort -z | xargs -0 sha256sum > models.sha256 )
cat > "$BUNDLE/IMPORT.txt" <<TXT
1. Transfer this directory through the approved corporate media path.
2. Verify docker-images.tar.sha256 and models.sha256.
3. Run: docker load -i docker-images.tar
4. Copy models/ into project/models/
5. Copy project/.env.airgap.example to project/.env and replace secrets/pinned images.
6. Set MGC_RUNTIME=${runtime} in .env.
7. Run: make up
8. Run: make acceptance
TXT
echo "Air-gap bundle prepared at: $BUNDLE"
