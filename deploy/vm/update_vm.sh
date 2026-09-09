#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

check_compose_version
require_cmd git
require_env_file

branch="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD)"
[[ "$branch" == "main" ]] || {
  echo "ERROR: update is allowed only from the main branch; current branch: $branch" >&2
  exit 2
}
if ! git -C "$ROOT_DIR" diff --quiet || ! git -C "$ROOT_DIR" diff --cached --quiet; then
  echo "ERROR: tracked repository files have local changes. Commit/stash them before update." >&2
  exit 2
fi

echo "Creating pre-update database backup..."
bash "$VM_DIR/backup_vm.sh"
old_sha="$(git -C "$ROOT_DIR" rev-parse HEAD)"

git -C "$ROOT_DIR" fetch --prune origin main
git -C "$ROOT_DIR" merge --ff-only origin/main
new_sha="$(git -C "$ROOT_DIR" rev-parse HEAD)"

echo "Updating containers: $old_sha -> $new_sha"
compose config --quiet
compose build --pull app
compose up -d db app nginx
wait_ready 90
bash "$VM_DIR/check_vm.sh"
echo "Update completed: $new_sha"
