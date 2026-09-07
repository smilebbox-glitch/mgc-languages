#!/usr/bin/env sh
set -eu
BASE="${BASE_URL:-http://localhost:3000/api/v1}"
for f in samples/*; do
  echo "Uploading $f"
  curl -fsS -X POST "$BASE/documents/upload" -F "file=@$f" -F "acl_groups=all" >/dev/null
 done
curl -fsS -X POST "$BASE/parts/8450012345/validate" >/dev/null
printf '\nRunning Design Review...\n'
curl -fsS -H 'Content-Type: application/json' -X POST "$BASE/design-reviews" \
  -d '{"part_number":"8450012345","baseline_revision":"C","revision":"D"}'
printf '\n\nRunning Change Impact...\n'
curl -fsS -H 'Content-Type: application/json' -X POST "$BASE/impact" \
  -d '{"part_number":"8450012345","from_revision":"C","to_revision":"D","max_depth":4}'
printf '\n\nDone. Open http://localhost:3000\n'
