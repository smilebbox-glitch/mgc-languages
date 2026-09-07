# MGC Engineering AI Local v6.3.26 — Operations Consolidation & `mgcctl`

## Цель

v6.3.26 уменьшает операционную сложность MGC. Проверенные механизмы backup/restore, rolling upgrade, blue/green, certification и provenance **не переписаны**: новый `mgcctl` является безопасным orchestration facade над существующими каноническими scripts.

## Основные команды

```bash
./mgcctl status
./mgcctl verify --scope quick
./mgcctl verify --scope security
./mgcctl verify --scope architecture
./mgcctl verify --scope release
./mgcctl verify --scope full
./mgcctl deploy --mode rolling --confirm DEPLOY
./mgcctl deploy --mode blue-green --confirm DEPLOY
./mgcctl rollback --mode blue-green --confirm ROLLBACK
./mgcctl backup --destination /approved/backup/path
./mgcctl restore --backup /approved/backup/path --confirm RESTORE
./mgcctl certify preflight --scope all
./mgcctl provenance --registry /approved/registry verify
./mgcctl diagnose --output mgc-diagnostic.json
```

Для машинной обработки большинство команд поддерживают `--json`; mutating/deployment commands поддерживают `--dry-run`.

## Fail-closed confirmations

- deployment: `--confirm DEPLOY`;
- rollback: `--confirm ROLLBACK`;
- restore: `--confirm RESTORE`;
- live load certification: `--confirm LOAD`.

CLI не использует `shell=True` для пользовательского ввода. Делегирование выполняется argv-массивами через `subprocess.run(..., shell=False)`.

## Backward compatibility

Старые Makefile targets и scripts остаются доступны. Это намеренно: v6.3.26 не ломает существующие runbooks и automation. `mgcctl` становится рекомендуемой operator-facing точкой входа, а старые команды — совместимым низкоуровневым слоем.

## Diagnostics privacy

`mgcctl diagnose` не сохраняет stdout/stderr внутренних preflight-команд, argv, secrets или raw environment. Отчёт содержит только имя проверки, status/return code и, при runtime-проверке, агрегированное число running services.

`mgcctl status` также не читает container environment/secrets. При отсутствии Docker CLI offline status остаётся доступным; `--require-runtime` позволяет fail-closed потребовать реальный runtime.

## Deployment semantics

`mgcctl deploy` не вводит новую deployment implementation:

- `rolling` → `scripts/rolling_upgrade.sh`;
- `blue-green` → `scripts/blue_green_cutover.sh`;
- `blue-green-finalize` → `scripts/blue_green_finalize.sh`;
- rollback → существующий guarded `scripts/blue_green_rollback.sh`.

Сертифицированное adjacent-patch окно: **6.3.25 ↔ 6.3.26**, schema остаётся **6.3.13**.

## Ограничения

`mgcctl` не превращает source-level checks в Production GO. Реальные Docker/HA/load/failover операции должны выполняться на approved target host. Production authorization остаётся отдельным human change-control решением.
