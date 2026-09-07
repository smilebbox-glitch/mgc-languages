#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/runtime_lib.sh
BACKUP_ROOT="${MGC_BACKUP_ROOT:-$ROOT/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${1:-$BACKUP_ROOT/mgc-$STAMP}"
TMP_REL=".mgc-backup/qdrant-$STAMP.snapshot"
TMP_HOST="$ROOT/storage/$TMP_REL"
mkdir -p "$DEST" "$(dirname "$TMP_HOST")"

command -v docker >/dev/null || { echo "ERROR: docker CLI is required on the approved runtime host" >&2; exit 2; }
PROFILE="${DEPLOYMENT_PROFILE:-$(env_value DEPLOYMENT_PROFILE "$ROOT")}"; PROFILE="${PROFILE:-ai}"
QUIESCE="${MGC_BACKUP_QUIESCE:-true}"
[[ "$QUIESCE" == true ]] || {
  if [[ "${MGC_ALLOW_UNQUIESCED_BACKUP:-false}" != true ]]; then
    echo "ERROR: v6.3.34 authoritative backup requires MGC_BACKUP_QUIESCE=true. Set MGC_ALLOW_UNQUIESCED_BACKUP=true only for a non-certifiable emergency copy." >&2
    exit 2
  fi
}

stack() { DEPLOYMENT_PROFILE="$PROFILE" MGC_STACK_QUIET=true ./scripts/stack.sh "$@"; }
mapfile -t AVAILABLE_SERVICES < <(stack config --services | grep -E '^[A-Za-z0-9_-]+$' || true)
mapfile -t RUNNING_SERVICES < <(stack ps --status running --services | grep -E '^[A-Za-z0-9_-]+$' || true)
STOPPED_BY_US=()

contains() { local needle="$1"; shift; local x; for x in "$@"; do [[ "$x" == "$needle" ]] && return 0; done; return 1; }
stop_if_running() {
  local svc="$1"
  contains "$svc" "${AVAILABLE_SERVICES[@]}" || return 0
  contains "$svc" "${RUNNING_SERVICES[@]}" || return 0
  stack stop "$svc" >/dev/null
  STOPPED_BY_US+=("$svc")
}

api_python() {
  if contains api "${RUNNING_SERVICES[@]}"; then
    stack exec -T api python "$@"
  else
    stack run --rm -T --no-deps api python "$@"
  fi
}

cleanup() {
  local rc=$?
  rm -f "$TMP_HOST" || true
  if ((${#STOPPED_BY_US[@]})); then
    # Start internal execution plane before ingress. Compose start is idempotent.
    local svc
    for svc in api worker worker-cpu worker-io worker-cad worker-ai beat gateway; do
      if contains "$svc" "${STOPPED_BY_US[@]}"; then stack start "$svc" >/dev/null 2>&1 || true; fi
    done
  fi
  exit "$rc"
}
trap cleanup EXIT

active_compute_jobs() {
  api_python - <<'PY'
from sqlalchemy import select, func
from app.db.models import ComputeJob
from app.db.session import SessionLocal
with SessionLocal() as db:
    print(int(db.scalar(select(func.count()).select_from(ComputeJob).where(ComputeJob.status == 'running')) or 0))
PY
}

if [[ "$QUIESCE" == true ]]; then
  echo "== Quiesce ingress and scheduler =="
  stop_if_running gateway
  stop_if_running beat

  DRAIN_TIMEOUT="${MGC_BACKUP_DRAIN_TIMEOUT_SECONDS:-120}"
  REQUIRE_CLEAN_DRAIN="${MGC_BACKUP_REQUIRE_CLEAN_DRAIN:-true}"
  deadline=$((SECONDS + DRAIN_TIMEOUT))
  active="$(active_compute_jobs | tail -1)"
  while [[ "$active" =~ ^[0-9]+$ ]] && (( active > 0 )) && (( SECONDS < deadline )); do
    echo "Waiting for $active managed compute job(s) to reach a safe boundary..."
    sleep 5
    active="$(active_compute_jobs | tail -1)"
  done
  if [[ "$active" =~ ^[0-9]+$ ]] && (( active > 0 )) && [[ "$REQUIRE_CLEAN_DRAIN" == true ]]; then
    echo "ERROR: $active managed compute job(s) are still running after ${DRAIN_TIMEOUT}s; authoritative backup refused." >&2
    echo "Use a larger MGC_BACKUP_DRAIN_TIMEOUT_SECONDS or an approved maintenance window." >&2
    exit 4
  fi

  echo "== Quiesce all background execution workers =="
  for svc in worker worker-cpu worker-io worker-cad worker-ai; do stop_if_running "$svc"; done
fi

EPOCH_ID="$(python - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
export MGC_BACKUP_CONSISTENCY_EPOCH_ID="$EPOCH_ID"
export MGC_BACKUP_QUIESCE_MODE="$QUIESCE"
export MGC_BACKUP_QUIESCED_SERVICES="$(IFS=,; echo "${STOPPED_BY_US[*]}")"

echo "== Authoritative consistency snapshot =="
api_python - "$EPOCH_ID" <<'PY' > "$DEST/CONSISTENCY_SNAPSHOT.json"
import json, sys
from app.db.session import SessionLocal
from app.services.dr_consistency import build_consistency_snapshot
with SessionLocal() as db:
    report = build_consistency_snapshot(db, hash_files=True, hash_database=True, epoch_id=sys.argv[1])
print(json.dumps(report, ensure_ascii=False, indent=2))
if report.get('status') != 'pass' or not report.get('policy', {}).get('backup_eligible'):
    raise SystemExit(5)
PY

echo "== Optional Qdrant rebuildable snapshot =="
BACKUP_DERIVED="${MGC_BACKUP_DERIVED:-true}"
if [[ "$BACKUP_DERIVED" == true && "$PROFILE" != core ]]; then
  if api_python - "$TMP_REL" <<'PYQ'
import json, sys
from pathlib import Path
import httpx
from app.core.config import get_settings
cfg=get_settings(); rel=sys.argv[1]
base=cfg.qdrant_url.rstrip('/'); collection=cfg.qdrant_collection
with httpx.Client(timeout=120.0) as c:
    r=c.post(f"{base}/collections/{collection}/snapshots"); r.raise_for_status()
    payload=r.json(); result=payload.get('result') or {}; name=result.get('name')
    if not name: raise SystemExit('Qdrant did not return a snapshot name')
    target=Path('/data/storage')/rel; target.parent.mkdir(parents=True, exist_ok=True)
    with c.stream('GET', f"{base}/collections/{collection}/snapshots/{name}") as d:
        d.raise_for_status()
        with target.open('wb') as fh:
            for chunk in d.iter_bytes(): fh.write(chunk)
    print(json.dumps({'collection':collection,'snapshot':name,'size_bytes':target.stat().st_size}))
PYQ
  then
    mv "$TMP_HOST" "$DEST/qdrant.snapshot"
  elif [[ "${MGC_REQUIRE_DERIVED_BACKUP:-false}" == true ]]; then
    echo "ERROR: Qdrant snapshot failed and MGC_REQUIRE_DERIVED_BACKUP=true" >&2
    exit 3
  else
    echo "WARN: Qdrant snapshot unavailable; vector index is rebuildable from authoritative evidence." >&2
  fi
else
  echo "Qdrant snapshot skipped (Core profile or MGC_BACKUP_DERIVED=false)."
fi

# The API is kept private while the consistency report and optional Qdrant snapshot are
# captured, then stopped so PostgreSQL + evidence storage cannot change during capture.
if [[ "$QUIESCE" == true ]]; then stop_if_running api; fi

echo "== PostgreSQL consistent dump =="
stack exec -T postgres pg_dump -U mgc -d mgc -Fc > "$DEST/postgres.dump"

echo "== Evidence storage archive =="
tar --exclude='./.mgc-backup' --exclude='./.mgc-backup/*' --exclude='./.mgc-ha' --exclude='./.mgc-ha/*' -C "$ROOT/storage" -czf "$DEST/storage.tar.gz" .

python scripts/backup_manifest.py "$DEST" >/dev/null
(
  cd "$DEST"
  sha256sum -c SHA256SUMS
)

echo "PASS: v6.3.34 authoritative consistency-verified backup created at $DEST"
echo "Consistency epoch: $EPOCH_ID"
echo "NOTE: Qdrant/Neo4j/read models are derived. PostgreSQL + evidence storage are authoritative and are fingerprint-bound in CONSISTENCY_SNAPSHOT.json."
