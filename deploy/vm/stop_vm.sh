#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_env_file
compose down --remove-orphans

echo "MGC Languages stopped. PostgreSQL volume vm_pgdata was preserved."
echo "To delete data, use an explicit disaster/rebuild procedure; this script never uses down -v."
