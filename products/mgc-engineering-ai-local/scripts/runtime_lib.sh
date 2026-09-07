#!/usr/bin/env bash
set -euo pipefail

mgc_root() { cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd; }

env_value() {
  local key="$1" root="$2" value=""
  if [[ -f "$root/.env" ]]; then
    value="$(grep -E "^${key}=" "$root/.env" | tail -1 | cut -d= -f2- || true)"
    value="${value%\"}"; value="${value#\"}"; value="${value%\'}"; value="${value#\'}"
  fi
  printf '%s' "$value"
}

has_gpu() {
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1
}

has_cpu_model() {
  local root="$1" f
  f="${CPU_MODEL_FILE:-$(env_value CPU_MODEL_FILE "$root")}"; f="${f:-Qwen3-4B-Q4_K_M.gguf}"
  [[ -f "$root/models/cpu/$f" ]]
}

has_cpu_vision_models() {
  local root="$1" model mmproj
  model="${CPU_VLM_MODEL_FILE:-$(env_value CPU_VLM_MODEL_FILE "$root")}"
  mmproj="${CPU_VLM_MMPROJ_FILE:-$(env_value CPU_VLM_MMPROJ_FILE "$root")}"
  [[ -n "$model" && -n "$mmproj" && -f "$root/models/cpu-vision/$model" && -f "$root/models/cpu-vision/$mmproj" ]]
}

select_runtime() {
  local root="$1" requested
  requested="${MGC_RUNTIME:-$(env_value MGC_RUNTIME "$root")}"; requested="${requested:-auto}"
  case "$requested" in
    cpu)
      has_cpu_model "$root" || { echo "ERROR: CPU model is missing. Run 'make prepare-cpu' on the connected staging machine." >&2; return 2; }
      printf 'cpu' ;;
    gpu)
      find "$root/models/generative" -type f -print -quit 2>/dev/null | grep -q . || { echo "ERROR: GPU generative model is missing. Run 'make prepare-models' on the connected staging machine." >&2; return 2; }
      printf 'gpu' ;;
    auto)
      if has_gpu && find "$root/models/generative" -type f -print -quit 2>/dev/null | grep -q .; then
        printf 'gpu'
      elif has_cpu_model "$root"; then
        printf 'cpu'
      else
        echo "ERROR: no usable runtime found. Stage models/cpu/<GGUF> for CPU or models/generative for GPU." >&2
        return 2
      fi ;;
    *) echo "ERROR: MGC_RUNTIME must be auto, cpu or gpu (got: $requested)" >&2; return 2 ;;
  esac
}

compose_args() {
  local root="$1" runtime="$2" vision="${3:-false}"
  printf '%s\n' "-f" "$root/docker-compose.airgap.yml" "-f" "$root/docker-compose.${runtime}.yml"
  if [[ "$runtime" == cpu && "$vision" == true ]]; then
    printf '%s\n' "-f" "$root/docker-compose.cpu-vision.yml"
  fi
  printf '%s\n' "-f" "$root/docker-compose.sso.yml"
}
