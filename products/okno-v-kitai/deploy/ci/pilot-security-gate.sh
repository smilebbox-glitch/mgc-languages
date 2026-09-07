#!/usr/bin/env bash
set -euo pipefail

npm ci
npm run pilot:preflight
npm run pilot:audit-deps

docker build -t "okno-v-kitai:${CI_COMMIT_SHA:-pilot-v1.6}" .

if command -v trivy >/dev/null 2>&1; then
  trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed "okno-v-kitai:${CI_COMMIT_SHA:-pilot-v1.6}"
else
  echo "WARN  trivy not installed; image CVE scan skipped. Configure the corporate image scanner or install Trivy."
fi
