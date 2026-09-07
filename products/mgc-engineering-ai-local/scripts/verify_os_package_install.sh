#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/backend/os-packages/runtime"
IMAGE="${PYTHON_BASE_IMAGE:-}"
[[ -n "$IMAGE" ]] || { echo "Set PYTHON_BASE_IMAGE to the approved immutable repo@sha256:digest" >&2; exit 2; }
[[ "$IMAGE" =~ @sha256:[0-9a-fA-F]{64}$ ]] || { echo "PYTHON_BASE_IMAGE must be immutable repo@sha256:digest" >&2; exit 2; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 2; }
python "$ROOT/backend/verify_os_package_bundle.py" "$BUNDLE" --expected-base-image "$IMAGE"
MANIFEST_SHA="$(python - "$BUNDLE/OS_PACKAGE_MANIFEST.json" <<'PY'
import hashlib,sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PY
)"
# Prove that the prepared .deb set can be installed against exactly the approved
# base image with networking disabled. This is an acceptance proof for the bundle;
# the later application Docker build repeats hash/receipt verification and uses no network.
docker run --rm --network none --user 0:0 -v "$BUNDLE:/bundle:ro" "$IMAGE" sh -euxc '
  test -s /bundle/OS_PACKAGE_MANIFEST.json
  set -- /bundle/*.deb
  test "$1" != "/bundle/*.deb"
  dpkg -i "$@"
  test -z "$(dpkg --audit)"
'
IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$IMAGE")"
python - "$BUNDLE" "$IMAGE" "$IMAGE_ID" "$MANIFEST_SHA" <<'PY'
from datetime import datetime, timezone
import json,sys
from pathlib import Path
root=Path(sys.argv[1]); image=sys.argv[2]; image_id=sys.argv[3]; manifest_sha=sys.argv[4]
manifest=json.loads((root/'OS_PACKAGE_MANIFEST.json').read_text())
receipt={
  'schema':'mgc.os-package-install-receipt.v1',
  'release':'6.3.34',
  'base_image':image,
  'base_image_local_id':image_id,
  'manifest_sha256':manifest_sha,
  'package_count':len(manifest.get('files') or []),
  'network_mode':'none',
  'installer':'dpkg -i',
  'result':'pass',
  'verified_at':datetime.now(timezone.utc).isoformat(),
}
(root/'OS_PACKAGE_INSTALL_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('WROTE',root/'OS_PACKAGE_INSTALL_RECEIPT.json')
PY
printf 'Offline OS package install verified with network disabled.\n'
