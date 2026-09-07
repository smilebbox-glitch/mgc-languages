# MGC Engineering AI Local v6.3.33 — Target-Host Deployment Assurance

## Назначение

v6.3.33 добавляет исполняемый fail-closed контур проверки целевых серверов перед rolling или blue/green deployment. Контур не заменяет load certification, CVE/SCA, backup/restore drill, integration certification или человеческое разрешение на production.

## Workflow

1. На каждом целевом application-host выполнить privacy-safe probe:

```bash
python scripts/target_host_probe.py \
  --node-id mgc-app-a \
  --profile 30 \
  --storage-path /var/lib/mgc \
  --output /controlled/evidence/mgc-app-a.host.json
```

2. Повторить probe для каждого `node_id` из `ops/multihost/topology.<profile>.json`.

3. Собрать deterministic certification report:

```bash
./mgcctl certify target-host \
  --profile 30 \
  --topology ops/multihost/topology.30.example.json \
  --evidence /controlled/evidence/mgc-app-a.host.json \
  --evidence /controlled/evidence/mgc-app-b.host.json \
  --output /controlled/evidence/target-host-assurance.json \
  --require-pass
```

Опционально report может быть подписан `--signing-key`; rollout может потребовать detached signature через `--require-signed-host-assurance`.

4. Перед deployment передать PASS report:

```bash
./mgcctl deploy \
  --mode rolling \
  --host-assurance /controlled/evidence/target-host-assurance.json \
  --confirm DEPLOY
```

Без report реальный rollout v6.3.33 не запускается. `--dry-run` разрешён без evidence, поскольку не меняет runtime.

## Проверяемый baseline host envelope

Для каждого узла проверяются:

- Linux host и поддерживаемая 64-bit architecture;
- CPU/RAM baseline по профилю 15/30/100;
- свободное место и disk-used ratio;
- фактический write → fsync → read → delete на указанном storage path;
- `RLIMIT_NOFILE`;
- наличие Docker CLI и доступность daemon;
- minimum Docker/Compose contract;
- синхронизация времени через `timedatectl` или `chronyc`;
- совпадение application release, DB schema и profile;
- полное one-to-one покрытие `node_id` из topology inventory.

Probe не собирает hostname, IP-адреса, environment variables или secrets.

## Fail-closed правила

`FAIL` формируется при любом обязательном missing/failed check, включая:

- evidence другого релиза или schema;
- отсутствующий topology node;
- duplicate/extra node evidence;
- недоступный Docker daemon;
- недостаточный host baseline;
- не синхронизированное/неопределённое время;
- неуспешный storage fsync probe;
- повреждённый canonical SHA-256 report.

Rolling и blue/green entrypoints повторно проверяют report через `target_host_deployment_guard.py` до обращения к Docker.

## Граница доверия

`decision=PASS` означает только соответствие target-host deployment envelope. Report всегда сохраняет:

- `production_authorized=false`;
- `performance_certified=false`;
- `human_approval_required=true`.

Production load, SLO/failover evidence, supply-chain provenance, CVE/SCA approvals, реальная integration certification и корпоративный change approval остаются отдельными gates.

## Версии

- Application: **6.3.33**
- Database schema: **6.3.13**
- DB migration: **нет**
- Adjacent rolling/blue-green window: **6.3.29 ↔ 6.3.30**
