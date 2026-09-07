#!/usr/bin/env sh
set -eu
BASE="${BASE_URL:-http://localhost:3000}"
for f in \
  samples/8450012345_REV_C_mounting_plate.step \
  samples/8450012345_REV_C_spec.txt \
  samples/8450012345_REV_D_mounting_plate.step \
  samples/8450012345_REV_D_spec_conflict.txt \
  samples/8450012345_REV_D_drawing_conflict.txt \
  samples/8450012345_REV_D_bom.csv
do
  echo "Uploading $f"
  curl -fsS -X POST "$BASE/api/v1/documents/upload" -F "file=@$f" -F "acl_groups=all" >/dev/null
  echo "  done"
done
echo "Demo dataset uploaded. Open $BASE and go to Part 360°."
