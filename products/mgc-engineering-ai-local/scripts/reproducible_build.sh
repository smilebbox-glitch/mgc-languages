#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
ENV_FILE="${MGC_REPRODUCIBLE_ENV_FILE:-.env.reproducible}"
export MGC_REPRODUCIBLE_ENV_FILE="$ENV_FILE"
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE; create it from approved immutable image digests." >&2; exit 2; }
export MGC_REQUIRE_REPRODUCIBLE_BUILD=true MGC_REQUIRE_LOCKFILES=true MGC_REQUIRE_CVE_SCANNER=true
python scripts/generate_build_inputs.py --env "$ENV_FILE"
export MGC_BUILD_SOURCE_SHA256="$(awk '{print $1}' supply-chain/BUILD_INPUTS.sha256)"
python scripts/supply_chain_preflight.py --strict --env "$ENV_FILE"
python scripts/dependency_lock_preflight.py
mkdir -p security-reports
SOURCE_CVE_REPORT="security-reports/CVE_SOURCE_SCAN_v6.3.34.txt"
IMAGE_CVE_REPORT="security-reports/CVE_IMAGE_SCAN_v6.3.34.txt"
./scripts/vulnerability_scan.sh 2>&1 | tee "$SOURCE_CVE_REPORT"
MGC_VERSION="${MGC_VERSION:-$(PYTHONPATH=backend python -c 'from app.core.runtime_contract import APP_VERSION; print(APP_VERSION)')}"; export MGC_VERSION MGC_BUILD_SOURCE_SHA256
: "${MGC_API_IMAGE:=mgc-engineering-ai-api:${MGC_VERSION}-local}"
: "${MGC_FRONTEND_IMAGE:=mgc-engineering-ai-frontend:${MGC_VERSION}-local}"
: "${MGC_GATEWAY_IMAGE:=mgc-engineering-ai-gateway:${MGC_VERSION}-local}"
: "${MGC_WEBHOOK_IMAGE:=mgc-engineering-ai-webhook-edge:${MGC_VERSION}-local}"
export MGC_API_IMAGE MGC_FRONTEND_IMAGE MGC_GATEWAY_IMAGE MGC_WEBHOOK_IMAGE
# --pull=false prevents registry substitution after immutable base images were approved/preloaded.
docker compose --env-file "$ENV_FILE" -f docker-compose.airgap.yml -f docker-compose.build.yml -f docker-compose.reproducible.yml build --pull=false api frontend gateway webhook-edge
./scripts/image_vulnerability_scan.sh 2>&1 | tee "$IMAGE_CVE_REPORT"
python scripts/generate_build_attestation.py --strict --cve-report "$SOURCE_CVE_REPORT" --cve-report "$IMAGE_CVE_REPORT"
python scripts/verify_build_attestation.py --strict
printf 'Reproducible-input application build completed with local attestation evidence. Production authorization still requires corporate change approval.\n'
