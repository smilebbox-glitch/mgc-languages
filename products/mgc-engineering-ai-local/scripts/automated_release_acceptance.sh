#!/usr/bin/env bash
set -euo pipefail

: "${MGC_RELEASE_ACCEPTANCE_CONFIRM:?Set MGC_RELEASE_ACCEPTANCE_CONFIRM=YES}"
[[ "$MGC_RELEASE_ACCEPTANCE_CONFIRM" == "YES" ]] || { echo "ERROR: MGC_RELEASE_ACCEPTANCE_CONFIRM must equal YES" >&2; exit 2; }
: "${PROFILE:?Set PROFILE=15|30|100}"
: "${BASE_URL:?Set BASE_URL=https://target}"
: "${PROJECT_CODE:?Set PROJECT_CODE=<certification fixture project>}"
: "${PART_NUMBER:?Set PART_NUMBER=<certification fixture part>}"
: "${TOPOLOGY:?Set TOPOLOGY=/path/topology.json}"
: "${EVIDENCE:?Set EVIDENCE=/path/failover-rto-rpo-evidence.json}"
: "${OUTPUT:?Set OUTPUT=/path/release-acceptance.json}"
: "${LOAD_SIGNING_KEY:?Set LOAD_SIGNING_KEY=/secure/path/load-signing-key.pem}"
: "${ACCEPTANCE_SIGNING_KEY:?Set ACCEPTANCE_SIGNING_KEY=/secure/path/acceptance-signing-key.pem}"

if [[ -n "${MGC_RELEASE_ACCEPTANCE_FAILOVER_CMD:-}" ]]; then
  [[ "${MGC_RELEASE_ACCEPTANCE_DISRUPTIVE_CONFIRM:-}" == "YES" ]] || {
    echo "ERROR: disruptive failover command requires MGC_RELEASE_ACCEPTANCE_DISRUPTIVE_CONFIRM=YES" >&2; exit 2;
  }
  bash -lc "$MGC_RELEASE_ACCEPTANCE_FAILOVER_CMD"
fi

[[ -s "$TOPOLOGY" && -s "$EVIDENCE" ]] || { echo "ERROR: topology/evidence input missing after optional drill" >&2; exit 2; }

work="$(mktemp -d -t mgc-release-acceptance-XXXXXX)"
trap 'rm -rf "$work"' EXIT
load="$work/load-evidence.json"
load_pub="$work/load-public.pem"
acceptance_pub="$work/acceptance-public.pem"
openssl pkey -in "$LOAD_SIGNING_KEY" -pubout -out "$load_pub" >/dev/null 2>&1
openssl pkey -in "$ACCEPTANCE_SIGNING_KEY" -pubout -out "$acceptance_pub" >/dev/null 2>&1

MGC_LOAD_CERTIFY_CONFIRM=YES python scripts/production_load_certify.py \
  --profile "$PROFILE" --base-url "$BASE_URL" --project-code "$PROJECT_CODE" --part-number "$PART_NUMBER" \
  --output "$load" --signing-key "$LOAD_SIGNING_KEY"

args=(
  --profile "$PROFILE" --topology "$TOPOLOGY" --evidence "$EVIDENCE"
  --load-evidence "$load" --load-signature "$load.sig" --load-public-key "$load_pub"
  --output "$OUTPUT" --signing-key "$ACCEPTANCE_SIGNING_KEY"
)
if [[ -n "${RELEASE_PROVENANCE_REGISTRY:-}" || -n "${RELEASE_PROVENANCE_KEY_ID:-}" ]]; then
  : "${RELEASE_PROVENANCE_REGISTRY:?Set RELEASE_PROVENANCE_REGISTRY}"
  : "${RELEASE_PROVENANCE_KEY_ID:?Set RELEASE_PROVENANCE_KEY_ID}"
  args+=(--provenance-registry "$RELEASE_PROVENANCE_REGISTRY" --provenance-key-id "$RELEASE_PROVENANCE_KEY_ID")
fi

if [[ -n "${BASELINE:-}" || -n "${BASELINE_SIGNATURE:-}" || -n "${BASELINE_PUBLIC_KEY:-}" ]]; then
  : "${BASELINE:?Set BASELINE with BASELINE_SIGNATURE and BASELINE_PUBLIC_KEY}"
  : "${BASELINE_SIGNATURE:?Set BASELINE_SIGNATURE}"
  : "${BASELINE_PUBLIC_KEY:?Set BASELINE_PUBLIC_KEY}"
  args+=(--baseline "$BASELINE" --baseline-signature "$BASELINE_SIGNATURE" --baseline-public-key "$BASELINE_PUBLIC_KEY")
fi
python scripts/release_acceptance_pipeline.py "${args[@]}"

echo "PASS: v6.3.34 release acceptance evidence created at $OUTPUT"
echo "NOTE: technical GO is not Production Authorization; human change control remains mandatory."
