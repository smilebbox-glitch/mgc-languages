#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/runtime_lib.sh
profile="${DEPLOYMENT_PROFILE:-$(env_value DEPLOYMENT_PROFILE "$ROOT")}"; profile="${profile:-ai}"
pitr="${MGC_PITR_ENABLED:-$(env_value MGC_PITR_ENABLED "$ROOT")}"; pitr="${pitr:-false}"
case "$profile" in core|ai|advanced) ;; *) echo "ERROR: DEPLOYMENT_PROFILE must be core, ai or advanced (got: $profile)" >&2; exit 2;; esac

if [[ "$profile" == core ]]; then
  [[ "${MGC_STACK_QUIET:-false}" == true ]] || echo "MGC runtime profile: CORE · deterministic engineering core"
  export DEPLOYMENT_PROFILE=core INFERENCE_RUNTIME=disabled
  CORE_FILES=(-f "$ROOT/docker-compose.airgap.yml" -f "$ROOT/docker-compose.sso.yml")
  if [[ "$pitr" == true ]]; then CORE_FILES+=(-f "$ROOT/docker-compose.pitr.yml"); fi
  exec docker compose "${CORE_FILES[@]}" "$@"
fi

runtime="$(select_runtime "$ROOT")"
vision="${MGC_CPU_VISION:-$(env_value MGC_CPU_VISION "$ROOT")}"; vision="${vision:-false}"
if [[ "$runtime" != cpu ]]; then vision=false; fi
if [[ "$runtime" == cpu ]]; then
  if [[ "${MGC_STACK_QUIET:-false}" == true ]]; then python scripts/cpu_capacity.py >/dev/null 2>&1 || true; else python scripts/cpu_capacity.py || true; fi
fi
mapfile -t FILES < <(compose_args "$ROOT" "$runtime" "$vision")
if [[ "$pitr" == true ]]; then FILES+=(-f "$ROOT/docker-compose.pitr.yml"); fi
[[ "${MGC_STACK_QUIET:-false}" == true ]] || echo "MGC inference runtime: ${runtime^^}$([[ "$vision" == true ]] && echo ' + CPU VISION') · profile=${profile^^}"
export INFERENCE_RUNTIME="$runtime" DEPLOYMENT_PROFILE="$profile"
exec docker compose "${FILES[@]}" --profile "$profile" "$@"
