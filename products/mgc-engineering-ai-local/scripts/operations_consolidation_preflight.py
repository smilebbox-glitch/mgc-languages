#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks=[]
def ck(name, ok):
    checks.append((name,bool(ok)))
    print(('PASS' if ok else 'FAIL')+': '+name)

def text(p): return (ROOT/p).read_text(encoding='utf-8')
rt=text(Path('backend/app/core/runtime_contract.py'))
cli=text(Path('scripts/mgcctl.py'))
launcher=text(Path('mgcctl'))
make=text(Path('Makefile'))
rolling=text(Path('scripts/rolling_upgrade.sh'))
blue=text(Path('scripts/blue_green_cutover.sh'))
restore=text(Path('scripts/restore_core.sh'))
backup=text(Path('scripts/backup_core.sh'))
prov=text(Path('scripts/release_provenance_registry.py'))

ck('runtime_version_6326', 'APP_VERSION = "6.3.34"' in rt and 'SCHEMA_VERSION = "6.3.13"' in rt)
ck('root_launcher', 'scripts/mgcctl.py' in launcher and '$@' in launcher)
ck('cli_schema', 'mgc.operations-cli.v1' in cli)
for command in ('status','verify','deploy','rollback','backup','restore','certify','provenance','drill','diagnose'):
    ck('command_'+command, f'sub.add_parser("{command}"' in cli)
ck('safe_subprocess_shell_false', 'shell=False' in cli and 'shell=True' not in cli)
ck('exact_deploy_confirmation', '_require(args.confirm, "DEPLOY", "deployment")' in cli)
ck('exact_rollback_confirmation', '_require(args.confirm, "ROLLBACK", "rollback")' in cli)
ck('exact_restore_confirmation', '_require(args.confirm, "RESTORE", "restore")' in cli)
ck('exact_load_confirmation', '_require(args.confirm, "LOAD", "live load certification")' in cli)
ck('dry_run_contract', 'DRY_RUN' in cli and '--dry-run' in cli)
ck('json_contract', 'mgc.operations-cli.v1' in cli and '--json' in cli)
ck('verify_scopes', all(f'"{x}"' in cli for x in ('quick','security','architecture','release','full')))
ck('delegates_rolling', 'scripts/rolling_upgrade.sh' in cli and 'rolling_upgrade_preflight.py' in rolling)
ck('delegates_blue_green', 'scripts/blue_green_cutover.sh' in cli and 'blue_green_cutover_preflight.py' in blue)
ck('delegates_backup', 'scripts/backup_core.sh' in cli and 'consistency-verified backup' in backup)
ck('delegates_restore', 'scripts/restore_core.sh' in cli and 'MGC_RESTORE_CONFIRM' in restore)
ck('delegates_provenance', 'scripts/release_provenance_registry.py' in cli and 'auditor-verify' in prov)
ck('offline_status', '--offline' in cli and '--require-runtime' in cli)
ck('diagnostic_privacy_boundary', 'compose", "ps", "--format", "json"' in cli and 'docker inspect' not in cli)
ck('make_preflight_target', 'operations-consolidation-preflight:' in make)
ck('resilience_certification_registered', 'resilience-certification' in cli and 'resilience-certification-preflight:' in make)
ck('make_old_targets_preserved', all(x in make for x in ('backup:','restore:','rolling-upgrade:','blue-green-rollback:','release-provenance-verify:')))
ck('adjacent_rollout_comment', '6.3.32 -> 6.3.34' in rolling and 'accept v6.3.32 task envelopes' in rolling)
ck('no_6326_db_migration', not (ROOT/'backend/app/db/migrations/versions/6.3.34').exists() and '6.3.34' not in text(Path('backend/app/db/migrations.py')))
failed=[n for n,ok in checks if not ok]
if failed: raise SystemExit('v6.3.34 operations consolidation preflight failed: '+', '.join(failed))
print(f'PASS: v6.3.34 Operations Consolidation preflight ({len(checks)}/{len(checks)})')
