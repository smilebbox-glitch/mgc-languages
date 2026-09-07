# High Availability & Failover Coordination — v6.3.18

## Scope

v6.3.18 provides **application-tier** HA controls for MGC Engineering AI Local while preserving PostgreSQL and evidence storage as authoritative engineering data. It does not claim full-stack, physical-host or availability-zone HA.

The base topology remains intentionally simple. HA is enabled only when the operator selects:

```bash
docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d
```

## HA topology

The overlay adds:

- `api-ha` — second stable API instance;
- `worker-ha` — second interactive worker;
- `worker-cpu-ha` — second CPU worker;
- `worker-io-ha` — second IO worker;
- `worker-cad-ha` — second CAD worker;
- `worker-ai-ha` — second AI worker when AI/Advanced profiles are enabled;
- `beat-ha` — second scheduler process, normally standby under the PostgreSQL advisory leader lock;
- `frontend-ha` — second static frontend instance;
- HA gateway template with primary/secondary API and frontend upstreams.

No HA overlay service publishes a new host port.

## API health and gateway failover

The base API now has a local `/api/v1/health/ready` container healthcheck. In HA mode this gives the gateway two independently health-observed API instances and also refreshes the ephemeral API deployment heartbeat.

The HA gateway uses Nginx passive upstream failure detection with:

- bounded `max_fails` / `fail_timeout`;
- `proxy_next_upstream` for connection/timeout/502/503/504 conditions;
- at most two upstream attempts.

The configuration deliberately does **not** enable Nginx `non_idempotent` retry. A POST/PATCH/PUT is therefore never blindly replayed after a partially failed upstream attempt. Existing domain idempotency keys, optimistic concurrency and transactional controls remain the correct write-safety mechanisms.

## Replica accounting

`high_availability_snapshot()` counts only components that are:

- runtime/schema compatible;
- `state=active`;
- API slot `stable` for stable API redundancy.

Candidate blue/green APIs do not count as stable redundancy. Draining APIs do not count either.

Default HA policy:

- minimum stable API replicas: 2;
- minimum replicas per required worker role: 2;
- required worker roles: interactive, CPU, IO;
- exactly one active scheduler leader;
- Redis registry remains diagnostic/non-authoritative.

## Degradation semantics

Loss of one API replica must not cause the surviving API to become not-ready solely because the cluster is under-replicated. That would create a cascading outage.

Therefore:

- one surviving compatible API => Core may continue serving, HA status `DEGRADED`;
- required replica targets observed => `HEALTHY`;
- incompatible runtime or two active Beat leaders => `UNSAFE`;
- Redis/component registry unavailable => `UNKNOWN`, never falsely `HEALTHY`;
- HA overlay disabled => `DISABLED`.

Core readiness continues to be based on authoritative PostgreSQL/evidence-storage safety plus the existing deployment-version rules.

## Scheduler split-brain protection

The v6.3.16 PostgreSQL session advisory lock remains the scheduler authority. With `beat` and `beat-ha` running:

- one instance acquires the leader lock and publishes schedules;
- the other publishes a `standby` heartbeat;
- if the lock-owning PostgreSQL session is lost, the active Beat terminates fail-closed;
- the standby instance can then acquire the lock;
- more than one observed active scheduler leader is reported as split-brain risk and `UNSAFE`.

Redis does not decide leadership.

## Worker loss tolerance

Workers retain:

- `task_acks_late=True`;
- `task_reject_on_worker_lost=True`;
- prefetch multiplier 1;
- resource-class queues;
- managed PostgreSQL job ledger and execution fencing from v6.3.13.

With duplicate worker roles in the HA overlay, loss of one worker leaves queue capacity on the surviving replica and unacknowledged work can be redelivered by Celery transport semantics.

## Operations and diagnostics

Engineering Admin endpoint:

```text
GET /api/v1/operations/high-availability
```

The snapshot exposes only sanitized operational topology:

- stable API replica count;
- active/standby scheduler counts;
- worker replica counts by role;
- redundancy gaps;
- split-brain risk;
- HA state and policy boundaries.

Prometheus metrics:

- `mgc_ha_api_replicas`;
- `mgc_ha_scheduler_leaders`;
- `mgc_ha_worker_replicas{role=...}`;
- `mgc_ha_ready`;
- `mgc_ha_split_brain_risk`.

The privacy-safe support bundle adds `high-availability.json`.

## Target-host failover drill

The drill is intentionally disruptive and requires explicit confirmation:

```bash
MGC_HA_DRILL_CONFIRM=YES make ha-drill
```

It verifies on a real Docker target:

1. two stable API replicas are observed;
2. gateway GET/liveness remains available after stopping one API;
3. CPU worker capacity remains after stopping one CPU worker;
4. after stopping one Beat process, exactly one active scheduler leader is observed;
5. split-brain is not observed;
6. stopped services are started again.

The drill proves only the tested container/service topology on that target.

## Explicit non-claims

v6.3.18 does not itself provide or certify:

- PostgreSQL primary/standby replication or database failover;
- distributed/shared evidence storage across physical hosts;
- HA for the external entrypoint/load balancer;
- multi-host or multi-zone orchestration;
- network partition fencing between physical nodes;
- zero-RPO/zero-RTO claims;
- Production GO.

For physical host or zone HA, PostgreSQL, evidence storage and the public entry/load-balancer layer must be provided by the company's approved infrastructure platform and tested independently.
