# MGC Engineering AI Local v6.3.20 — Multi-host Production Topology & External Load-Balancer Safety

## Goal

Extend the v6.3.18 application-tier HA and v6.3.19 authoritative DB/evidence fencing from one Compose target to a controlled **multi-host application topology** without turning Docker Compose, Redis telemetry or MGC itself into an infrastructure quorum manager.

v6.3.20 does **not** change the automotive business schema. Application version is `6.3.20`; database schema remains `6.3.13`.

## Runtime placement identity

Every active runtime heartbeat may carry:

- `topology_node_id` — stable per-host/VM application-node identity;
- `topology_failure_domain` — independent host/rack/zone domain used for anti-affinity checks;
- `topology_node_role` — operational placement label.

These fields are operational metadata only. They do not grant RBAC/ACL rights and Redis remains ephemeral telemetry, never engineering truth.

`GET /api/v1/operations/multi-host-topology` reports compatible active stable APIs and workers by failure domain, missing labels, required worker-role spread and node-identity conflicts. Under-replication is `DEGRADED`; it does not deliberately make the surviving API unready and cause a cascading outage. Runtime/version conflicts or the same node id appearing in multiple failure domains are `UNSAFE`.

## External load-balancer health contract

`GET /api/v1/health/lb` is a deliberately small unauthenticated system endpoint for an external LB. It returns only:

- contract id `mgc-external-lb-v1`;
- `eligible` / `ineligible` status;
- `traffic_eligible` boolean;
- application version;
- schema version.

It does not expose dependency names, endpoint addresses, topology labels or internal readiness details. Eligibility is based on local application readiness, including authoritative DB/evidence fencing when that mode is enabled.

The reference `ops/external-lb/haproxy.cfg.example` uses active health checks and **`retries 0`**, with no request redispatch/retry policy. If a host dies during a non-idempotent write, the in-flight request may fail; the LB does not blindly replay the same write to another node. Subsequent requests are directed only to healthy nodes. Application retry remains governed by existing idempotency/domain controls.

## Per-node deployment overlay

`docker-compose.multihost.yml` is applied **independently on every app host**. It is not a cross-host orchestrator.

It requires explicit:

- `MGC_NODE_ID`;
- `MGC_FAILURE_DOMAIN`;
- `MGC_NODE_BIND_IP` for the per-node gateway;
- external/shared `DATABASE_URL`;
- external/shared `REDIS_URL`;
- expected PostgreSQL system identifier;
- evidence cluster id / approved evidence path.

The overlay enables v6.3.19 database/evidence fencing and only publishes the gateway. API/workers remain internal to the node's Compose network.

## Placement certification profiles

Reference inventories are provided under `ops/multihost/` for **15, 30 and 100 engineer topology profiles**.

```bash
python scripts/topology_certify.py --inventory ops/multihost/topology.15.example.json --profile 15
python scripts/topology_certify.py --inventory ops/multihost/topology.30.example.json --profile 30
python scripts/topology_certify.py --inventory ops/multihost/topology.100.example.json --profile 100
```

The 15/30 profiles require at least two API failure domains and two failure domains for interactive/CPU/IO workers. The 100 profile reference requires three API failure domains and at least two worker failure domains for those required roles.

These profiles certify **placement policy only**. The result always records `performance_certified=false` and `production_authorized=false`. Actual 15/30/100-engineer throughput, latency, connection-pool saturation and AI/CAD workload capacity must be measured on the target hardware.

## Deployment guard

Before draining/cutting over another multi-host node, export the current Engineering Admin topology snapshot and run:

```bash
python scripts/multihost_deployment_guard.py --snapshot topology.json
```

The guard fails closed unless the registry is available, topology is `HEALTHY`, all required labels are present, there are no node/failure-domain identity conflicts and no required worker-domain gaps.

## Host-loss drill harness

A disruptive target-host harness is provided:

```bash
MGC_MULTHOST_DRILL_CONFIRM=YES \
MGC_EXTERNAL_LB_PROBE_URL=https://lb.example/api/v1/health/lb \
MGC_HOST_FAILURE_INJECT_CMD='<approved host isolation command>' \
MGC_HOST_RECOVER_CMD='<approved host recovery command>' \
make multihost-drill
```

The harness first proves the external LB baseline, executes an operator-supplied approved fault injection, waits for an eligible LB path through surviving capacity, then executes the supplied recovery command. It cannot be run accidentally and MGC does not invent host-management privileges.

## Authority boundary

v6.3.20 still does **not** implement:

- PostgreSQL quorum or promotion;
- STONITH/fencing of physical servers;
- evidence-storage replication;
- external load-balancer cluster HA;
- rack/zone placement enforcement;
- performance certification;
- automatic Production GO.

Those remain corporate infrastructure and change-control responsibilities. `production_authorized=false` remains explicit.
