#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_env_file
compose config --quiet
compose up -d db app nginx
wait_ready 90
bash "$VM_DIR/check_vm.sh"
echo "MGC Languages started: $(public_url)"
