# MGC Engineering AI Local v6.3.17 — Blue/Green Cutover & Automated Rollback Safety

## Goal

v6.3.17 closes the API traffic-cutover gap left intentionally open in v6.3.16. The normal Compose topology remains unchanged. A separate `docker-compose.bluegreen.yml` overlay starts an isolated `api-candidate` and `frontend-candidate` while the canonical `api`/`frontend` continue serving production traffic.

Database schema remains **6.3.13**. No v6.3.17 database migration exists.

## Stable and candidate slots

The base deployment uses `DEPLOYMENT_SLOT=stable` by default. The candidate API runs with `DEPLOYMENT_SLOT=candidate`. Runtime component heartbeats include this slot as ephemeral deployment telemetry; Redis remains diagnostic infrastructure and never becomes engineering truth.

The candidate services expose only the internal Compose network. They do not publish host ports.

## Gateway switching

The gateway template now resolves two explicit environment-controlled upstreams:

- `API_UPSTREAM`, default `api:8080`;
- `FRONTEND_UPSTREAM`, default `frontend:8080`.

Therefore ordinary `docker compose up` retains the original topology. Blue/green cutover recreates only the gateway with candidate upstreams after acceptance.

## Candidate acceptance

`make blue-green-cutover` performs, in order:

1. v6.3.17 static blue/green preflight;
2. Compose configuration validation on the target host;
3. source stable runtime contract discovery from the running API container;
4. fail-closed version/schema compatibility check;
5. candidate API/frontend startup on the internal network;
6. candidate runtime-contract verification;
7. multiple consecutive candidate readiness samples (default 3);
8. gateway switch to the candidate;
9. multiple post-switch samples (default 5).

A corporate synthetic/SLO command may be supplied through `CUTOVER_SLO_PROBE_CMD`. A failed probe counts exactly like failed readiness.

## Automated rollback

Post-switch consecutive failures are counted. Default rollback threshold is 2. When reached, `blue_green_cutover.sh` invokes the guarded rollback path.

Rollback is permitted only when:

- source and rollback target have identical database schema versions;
- major/minor application versions match;
- rollback target is not newer than the currently active candidate;
- patch rollback distance is within `CUTOVER_MAX_PATCH_ROLLBACK_SKEW` (default 1).

For the certified v6.3.16 → v6.3.17 transition this means `6.3.17 / schema 6.3.13` can automatically route back to `6.3.16 / schema 6.3.13`. A schema-changing release must not use automatic traffic rollback; it requires an explicit restore/forward-fix procedure.

After rollback, candidate services are intentionally left isolated for diagnostics instead of being destroyed automatically.

## Operational state

The cutover script writes only minimal operational metadata to `storage/.mgc-deployment/bluegreen.env` and protects the file with mode 0600. It contains runtime versions/schema and state (`switching`, `candidate_active`, `rolled_back`, `finalized`), not engineering data or credentials.

## Finalization

Successful cutover does not automatically replace the canonical stable fleet. After the observation/change-approval window, an operator explicitly runs:

```bash
make blue-green-finalize
```

Finalization reuses the v6.3.16/v6.3.17 worker-drain, scheduler leader, task-envelope and version-skew controls to upgrade workers/Beat/canonical API, returns the gateway to canonical `api:8080`/`frontend:8080`, then stops candidate services.

Production authorization remains a separate human corporate gate.

## Commands

```bash
make blue-green-preflight
make blue-green-cutover
make blue-green-rollback
make blue-green-finalize
```

## Non-goals / target-host gates

The source package does not claim a live Docker blue/green drill because the packaging environment has no Docker CLI/daemon. Corporate acceptance must execute the full cutover, forced candidate failure, guarded rollback, post-rollback readiness, observation-window SLO probe and finalization on the target deployment topology.

v6.3.17 also does not claim arbitrary cross-schema rollback, database rollback by traffic routing, Kubernetes service-mesh semantics, or automatic Production GO.
