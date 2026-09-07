#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/backend/os-packages/runtime"
IMAGE="${PYTHON_BASE_IMAGE:-}"
[[ -n "$IMAGE" ]] || { echo "Set PYTHON_BASE_IMAGE to an approved repo@sha256:digest" >&2; exit 2; }
[[ "$IMAGE" =~ @sha256:[0-9a-fA-F]{64}$ ]] || { echo "PYTHON_BASE_IMAGE must be immutable repo@sha256:digest" >&2; exit 2; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 2; }
rm -rf "$OUT"
mkdir -p "$OUT"
PACKAGES=(libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 libgomp1 libegl1 libopengl0)
# Corporate network/mirror policy controls the configured APT source used by the approved base image.
# This preparation step may use the approved mirror; the later application build is fully offline.
docker run --rm --user 0:0 -v "$OUT:/out" "$IMAGE" sh -euxc '
  apt-get update
  apt-get install -y --download-only --no-install-recommends "$@"
  cp -a /var/cache/apt/archives/*.deb /out/
' sh "${PACKAGES[@]}"
python - "$OUT" "$IMAGE" <<'PY'
import hashlib, json, subprocess, sys
from pathlib import Path
out=Path(sys.argv[1]); image=sys.argv[2]
files=[]
for p in sorted(out.glob('*.deb')):
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        meta=subprocess.check_output(['dpkg-deb','-f',str(p),'Package','Version','Architecture'],text=True).splitlines()
        package,version,arch=(meta+['','',''])[:3]
    except Exception:
        package=version=arch='unknown'
    files.append({'name':p.name,'sha256':h,'bytes':p.stat().st_size,'package':package,'version':version,'architecture':arch})
if not files: raise SystemExit('No .deb files downloaded')
manifest={'schema':'mgc.os-package-bundle.v1','release':'6.3.34','base_image':image,'files':files}
(out/'OS_PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('WROTE',out/'OS_PACKAGE_MANIFEST.json',len(files),'packages')
PY
"$ROOT/scripts/verify_os_package_install.sh"
printf 'Prepared and offline-install-verified OS package bundle from approved base image/mirror.\n'
