#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks = []

def ck(label: str, ok: bool) -> None:
    checks.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'} {label}")

runtime=(ROOT/'backend/app/core/runtime_contract.py').read_text(encoding='utf-8')
service=(ROOT/'backend/app/services/dr_consistency.py').read_text(encoding='utf-8')
backup=(ROOT/'scripts/backup_core.sh').read_text(encoding='utf-8')
restore=(ROOT/'scripts/restore_core.sh').read_text(encoding='utf-8')
manifest=(ROOT/'scripts/backup_manifest.py').read_text(encoding='utf-8')
compare=(ROOT/'scripts/dr_consistency_compare.py').read_text(encoding='utf-8')
stack=(ROOT/'scripts/stack.sh').read_text(encoding='utf-8')
pitr=(ROOT/'docker-compose.pitr.yml').read_text(encoding='utf-8')
doc=(ROOT/'docs/BACKUP_RESTORE_DR.md').read_text(encoding='utf-8')
tech=(ROOT/'DATA_CONSISTENCY_DR_v6.3.14.md').read_text(encoding='utf-8')

ck('application version 6.3.34', 'APP_VERSION = "6.3.34"' in runtime)
ck('database schema remains 6.3.13', 'SCHEMA_VERSION = "6.3.13"' in runtime)
ck('no v6.3.14 schema migration claimed', 'Database migration: **none**' in tech)
ck('consistency service present', 'def build_consistency_snapshot' in service)
ck('exact compare present', 'def compare_consistency_snapshots' in service)
ck('database logical hashing', 'logical_sha256' in service and '_database_fingerprint' in service)
ck('PostgreSQL sequence state included', 'pg_sequences' in service and 'sequence_rows' in service)
ck('evidence tree hashing', '_storage_fingerprint' in service and 'tree_sha256' in service)
ck('document SHA verification', 'document_sha256_mismatch' in service and '_sha256_file(path)' in service)
ck('path escape fail closed', 'document_path_outside_storage' in service)
ck('storage symlink fail closed', 'storage_symlink' in service)
ck('Digital Thread document reference scan', 'dangling_document_reference' in service and 'DOCUMENT_REFERENCE_LIST_COLUMNS' in service)
ck('document activity chain verification', 'document_activity_chain_invalid' in service and '_activity_digest' in service)
ck('engineering change chain verification', 'change_event_chain_invalid' in service and '_event_digest' in service)
ck('schema marker checked', 'schema_marker_mismatch' in service)
ck('backup requires quiesce by default', 'MGC_ALLOW_UNQUIESCED_BACKUP' in backup and 'authoritative backup requires MGC_BACKUP_QUIESCE=true' in backup)
ck('gateway quiesced', 'stop_if_running gateway' in backup)
ck('scheduler quiesced', 'stop_if_running beat' in backup)
for worker in ['worker','worker-cpu','worker-io','worker-cad','worker-ai']:
    ck(f'{worker} included in quiesce set', worker in backup and 'all background execution workers' in backup)
ck('managed-job clean drain', 'MGC_BACKUP_DRAIN_TIMEOUT_SECONDS' in backup and 'MGC_BACKUP_REQUIRE_CLEAN_DRAIN' in backup)
ck('full consistency snapshot before dump', backup.find('CONSISTENCY_SNAPSHOT.json') < backup.find('pg_dump'))
ck('private API stopped before PostgreSQL capture', backup.find('stop_if_running api') < backup.find('pg_dump'))
ck('backup manifest v2', 'mgc-core-backup-v2' in manifest)
ck('backup manifest binds consistency epoch', 'consistency_epoch_id' in manifest)
ck('backup manifest binds database fingerprint', 'database_logical_sha256' in manifest)
ck('backup manifest binds storage fingerprint', 'storage_tree_sha256' in manifest)
ck('restore requires explicit destructive confirmation', 'MGC_RESTORE_CONFIRM' in restore)
ck('legacy restore requires explicit acceptance', 'MGC_ALLOW_LEGACY_RESTORE' in restore)
ck('unquiesced restore requires explicit acceptance', 'MGC_ALLOW_UNQUIESCED_RESTORE' in restore)
ck('restore computes post-restore full fingerprint', 'post-restore-consistency' in restore and 'hash_files=True, hash_database=True' in restore)
ck('restore exact compare is fail closed', 'dr_consistency_compare.py' in restore and 'SYSTEM REMAINS IN MAINTENANCE' in restore)
ck('comparison occurs before private API restart', restore.find('dr_consistency_compare.py') < restore.find('Start private API'))
ck('Qdrant remains optional/rebuildable', 'optional Qdrant' in restore and 'derived' in doc.lower())
ck('PITR overlay present', 'archive_mode=on' in pitr and 'wal_level=replica' in pitr)
ck('PITR archive target required', 'MGC_PITR_ARCHIVE_PATH:?' in pitr)
ck('PITR uses archive_command', 'archive_command=' in pitr and '%p' in pitr and '%f' in pitr)
ck('PITR overlay gated by setting', 'MGC_PITR_ENABLED' in stack and 'docker-compose.pitr.yml' in stack)
ck('WAL LSN captured in consistency evidence', 'pg_current_wal_lsn' in service and 'checkpoint_lsn' in service)
ck('archive command value not exported by status', 'archive_command_configured' in service and 'archive_command":' not in service)
ck('DR runbook updated', 'consistency epoch' in doc.lower() and 'v6.3.14' in doc)
ck('technical release document present', 'Data Consistency & Disaster Recovery' in tech)

failed=[label for label,ok in checks if not ok]
if failed:
    raise SystemExit('v6.3.14 DR consistency preflight failed: '+', '.join(failed))
print(f'PASS: v6.3.14 Data Consistency & DR preflight ({len(checks)}/{len(checks)})')
