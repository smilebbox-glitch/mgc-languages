#!/usr/bin/env bash
set -euo pipefail
npm run pilot:security
npm run pilot:operations
npm run pilot:types
npm run pilot:sbom
if [[ "${RUN_NPM_AUDIT:-0}" == "1" ]]; then
  npm run pilot:audit-deps
else
  echo "INFO  npm audit skipped (set RUN_NPM_AUDIT=1 in online CI to enable advisory check)"
fi
