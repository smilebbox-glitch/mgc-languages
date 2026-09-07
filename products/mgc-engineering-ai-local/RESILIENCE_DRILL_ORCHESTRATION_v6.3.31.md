# MGC Engineering AI Local v6.3.31 — Resilience Drill Orchestration

## Назначение

v6.3.31 добавляет управляемый контур проверки отказоустойчивости. Он **не является chaos monkey** и не даёт системе права самостоятельно выключать инфраструктуру в production. По умолчанию `mgcctl drill` только строит/валидирует план. Live-инъекция требует явного `--confirm DRILL` и использует только заранее определённые Docker Compose действия без произвольного shell.

Application version: **6.3.31**  
Database schema: **6.3.13**  
Database migration: **none**

## Сценарии

| Scenario | Target | Production default | Blast radius |
|---|---|---:|---|
| `api_instance_loss` | `api` | allowed with explicit DRILL confirmation | single API replica |
| `worker_cpu_loss` | `worker-cpu` | allowed with explicit DRILL confirmation | single CPU worker |
| `redis_brownout` | `redis` | blocked by default | ephemeral coordination / queue dependency |
| `qdrant_brownout` | `qdrant` | blocked by default | AI semantic-search enrichment |
| `integration_gateway_timeout` | `integration-simulator` | blocked by default | one external integration gateway |

Dependency drills in production require **both** `--allow-production-dependency-drill` and a non-empty `--maintenance-window-ref`. Qdrant drill is valid only for `ai` / `advanced` profiles.

## Governance

- arbitrary shell injection: **forbidden**;
- default execution: **plan-only**;
- explicit `DRILL` confirmation required for live execution;
- recovery step is mandatory and runs from a `finally` boundary;
- maximum requested fault window is bounded to 1–120 seconds;
- no engineering-data or database mutation is authorized by the drill contract;
- a simulation can produce only `SIMULATED`, never `PASS` evidence;
- a live `PASS` requires fault injection + service continuity + recovery attempt + recovery success;
- resilience evidence never authorizes production;
- no automatic root-cause claim is made.

## Evidence contracts

Plan: `mgc.resilience-drill-plan.v1`  
Execution evidence: `mgc.resilience-drill-evidence.v1`

Both use canonical JSON SHA-256 integrity. Evidence intentionally stores bounded booleans/timings/status codes instead of raw Docker output, logs, credentials, document content or engineering identifiers.

### Incident-evidence binding

A completed drill can be bound to `mgc.production-incident-evidence.v1`. The binding copies only:

- incident evidence SHA-256;
- bounded signal codes;
- signal count/status;
- intersection of expected and observed signal codes.

Raw signal payloads, summaries and evidence details are **not copied**. The binding is correlation evidence only and never asserts root cause.

## CLI

```text
./mgcctl drill catalog

./mgcctl drill plan \
  --scenario api_instance_loss \
  --scenario worker_cpu_loss \
  --tier production \
  --profile core \
  --output drill-plan.json

./mgcctl drill run \
  --plan drill-plan.json \
  --confirm DRILL \
  --output drill-evidence.json

./mgcctl drill bind \
  --evidence drill-evidence.json \
  --incident-evidence incident-evidence.json \
  --output drill-evidence.bound.json

./mgcctl drill validate --kind evidence --file drill-evidence.bound.json
```

For a dry rehearsal without Docker mutation:

```text
./mgcctl drill run --plan drill-plan.json --simulate --output simulated.json
```

`SIMULATED` evidence is useful for workflow verification only and is never certifiable live evidence.

## Boundaries

This layer verifies application/dependency recovery behavior on the target topology. It does **not** replace PostgreSQL/evidence HA certification, backup/restore verification, physical host failover, load certification, integration certification, CVE/SCA approval or human change authorization.
