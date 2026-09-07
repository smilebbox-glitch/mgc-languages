#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source scripts/runtime_lib.sh
SRC="${1:-}"
[[ -n "$SRC" && -d "$SRC" ]] || { echo "Usage: MGC_RESTORE_CONFIRM=RESTORE $0 <backup-dir>" >&2; exit 2; }
[[ "${MGC_RESTORE_CONFIRM:-}" == "RESTORE" ]] || { echo "ERROR: set MGC_RESTORE_CONFIRM=RESTORE for this destructive operation" >&2; exit 2; }
for f in BACKUP_MANIFEST.json SHA256SUMS postgres.dump storage.tar.gz; do [[ -f "$SRC/$f" ]] || { echo "ERROR: missing $f" >&2; exit 2; }; done
(cd "$SRC" && sha256sum -c SHA256SUMS)
PROFILE="${DEPLOYMENT_PROFILE:-$(env_value DEPLOYMENT_PROFILE "$ROOT")}"; PROFILE="${PROFILE:-ai}"
stack() { DEPLOYMENT_PROFILE="$PROFILE" MGC_STACK_QUIET=true ./scripts/stack.sh "$@"; }

MANIFEST_SCHEMA="$(python - "$SRC/BACKUP_MANIFEST.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding='utf-8')).get('schema',''))
PY
)"
case "$MANIFEST_SCHEMA" in
  mgc-core-backup-v2)
    [[ -f "$SRC/CONSISTENCY_SNAPSHOT.json" ]] || { echo "ERROR: v2 backup is missing CONSISTENCY_SNAPSHOT.json" >&2; exit 2; }
    CERTIFIABLE="$(python - "$SRC/BACKUP_MANIFEST.json" <<'PY'
import json,sys
print('true' if json.load(open(sys.argv[1],encoding='utf-8')).get('certifiable_authoritative_backup') else 'false')
PY
)"
    if [[ "$CERTIFIABLE" != true && "${MGC_ALLOW_UNQUIESCED_RESTORE:-false}" != true ]]; then
      echo "ERROR: backup was not created under a certified quiesce. Set MGC_ALLOW_UNQUIESCED_RESTORE=true only under approved incident handling." >&2
      exit 2
    fi
    ;;
  mgc-core-backup-v1)
    if [[ "${MGC_ALLOW_LEGACY_RESTORE:-false}" != true ]]; then
      echo "ERROR: legacy v1 backup has no authoritative consistency fingerprint. Set MGC_ALLOW_LEGACY_RESTORE=true for an explicitly accepted legacy restore." >&2
      exit 2
    fi
    echo "WARN: restoring legacy v1 backup without exact DB/evidence fingerprint comparison." >&2
    ;;
  *) echo "ERROR: unsupported backup manifest schema: $MANIFEST_SCHEMA" >&2; exit 2;;
esac

if [[ "${MGC_SKIP_PRE_RESTORE_BACKUP:-false}" != true ]]; then
  echo "== Safety backup of current state =="
  DEPLOYMENT_PROFILE="$PROFILE" MGC_BACKUP_QUIESCE=true ./scripts/backup_core.sh
fi

mapfile -t AVAILABLE_SERVICES < <(stack config --services | grep -E '^[A-Za-z0-9_-]+$' || true)
contains() { local needle="$1"; shift; local x; for x in "$@"; do [[ "$x" == "$needle" ]] && return 0; done; return 1; }
stop_if_available() { local svc="$1"; contains "$svc" "${AVAILABLE_SERVICES[@]}" && stack stop "$svc" >/dev/null 2>&1 || true; }
start_if_available() { local svc="$1"; contains "$svc" "${AVAILABLE_SERVICES[@]}" && stack start "$svc" >/dev/null 2>&1 || true; }
api_run_python() { stack run --rm -T --no-deps api python "$@"; }

# Failures after this point deliberately leave ingress/workers stopped. Recovery must not
# become visible merely because containers can start.
echo "== Enter restore maintenance state =="
for svc in gateway beat worker worker-cpu worker-io worker-cad worker-ai api; do stop_if_available "$svc"; done

echo "== Restore PostgreSQL =="
stack exec -T postgres psql -U mgc -d mgc -v ON_ERROR_STOP=1 -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
stack exec -T postgres pg_restore -U mgc -d mgc --no-owner --no-privileges < "$SRC/postgres.dump"

echo "== Restore authoritative evidence storage =="
mkdir -p "$ROOT/storage"
find "$ROOT/storage" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
tar -C "$ROOT/storage" -xzf "$SRC/storage.tar.gz"
mkdir -p "$ROOT/storage/.mgc-backup"

if [[ "$MANIFEST_SCHEMA" == "mgc-core-backup-v2" ]]; then
  echo "== Verify authoritative restore against backup consistency epoch =="
  ACTUAL="$(mktemp "$ROOT/storage/.mgc-backup/post-restore-consistency.XXXXXX.json")"
  COMPARE="$(mktemp "$ROOT/storage/.mgc-backup/post-restore-compare.XXXXXX.json")"
  api_run_python - <<'PY' > "$ACTUAL"
import json
from app.db.session import SessionLocal
from app.services.dr_consistency import build_consistency_snapshot
with SessionLocal() as db:
    report = build_consistency_snapshot(db, hash_files=True, hash_database=True)
print(json.dumps(report, ensure_ascii=False, indent=2))
if report.get('status') != 'pass':
    raise SystemExit(5)
PY
  if ! python scripts/dr_consistency_compare.py "$SRC/CONSISTENCY_SNAPSHOT.json" "$ACTUAL" --output "$COMPARE"; then
    echo "ERROR: restored authoritative state does not match the backup consistency epoch." >&2
    cat "$COMPARE" >&2 || true
    echo "SYSTEM REMAINS IN MAINTENANCE: gateway/workers/api are not restarted." >&2
    exit 5
  fi
  echo "PASS: PostgreSQL + evidence storage exactly match the recorded consistency epoch."
  rm -f "$ACTUAL" "$COMPARE"
fi

if [[ -f "$SRC/qdrant.snapshot" ]]; then
  echo "== Recover optional Qdrant snapshot =="
  cp "$SRC/qdrant.snapshot" "$ROOT/storage/.mgc-backup/restore.snapshot"
  api_run_python - <<'PYQ'
from pathlib import Path
import httpx
from app.core.config import get_settings
cfg=get_settings(); p=Path('/data/storage/.mgc-backup/restore.snapshot')
if not cfg.semantic_search_enabled:
    print('Qdrant snapshot present but semantic search is disabled; index remains rebuildable and restore is skipped.')
    raise SystemExit(0)
url=f"{cfg.qdrant_url.rstrip('/')}/collections/{cfg.qdrant_collection}/snapshots/upload"
with p.open('rb') as fh, httpx.Client(timeout=300.0) as c:
    r=c.post(url, params={'priority':'snapshot'}, files={'snapshot':(p.name,fh,'application/octet-stream')})
    r.raise_for_status()
print('Qdrant snapshot restore requested successfully')
PYQ
  rm -f "$ROOT/storage/.mgc-backup/restore.snapshot"
fi

echo "== Start private API and verify readiness =="
start_if_available api
for _ in $(seq 1 60); do
  if stack exec -T api python - <<'PYL' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health/live', timeout=2).read()
PYL
  then break; fi
  sleep 2
done

stack exec -T api python - <<'PYR'
import json, urllib.request
try:
    r=urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health/ready', timeout=10)
    payload=json.loads(r.read())
except Exception as exc:
    raise SystemExit(f'RESTORE NOT READY: {exc}')
if payload.get('status')!='ready': raise SystemExit(f'RESTORE NOT READY: {payload}')
print(json.dumps(payload,ensure_ascii=False,indent=2))
PYR

echo "== Re-open execution plane =="
for svc in worker worker-cpu worker-io worker-cad worker-ai beat gateway; do start_if_available "$svc"; done

echo "PASS: authoritative restore completed, consistency epoch verified, and readiness is green."
echo "Rebuild/observe derived projections (Qdrant/Neo4j/read models) as required, then execute engineer smoke tests."
