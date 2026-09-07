# v6.3.21 — Production Topology Certification & SLO Enforcement

## Scope

v6.3.21 converts the v6.3.20 placement references for 15/30/100 engineers into a fail-closed production acceptance contract. It does **not** change automotive-domain data or the database schema; the application is 6.3.21 and the schema remains 6.3.13.

## Certification profiles

| Profile | Named users | Target concurrent | Min API failure domains | Dependency availability | HTTP p95 | Max error rate | RTO | RPO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15 | 15 | 5 | 2 | 99.5% | 500 ms | 1.0% | 300 s | 300 s |
| 30 | 30 | 10 | 2 | 99.7% | 500 ms | 1.0% | 180 s | 120 s |
| 100 | 100 | 30 | 3 | 99.9% | 750 ms | 0.5% | 120 s | 60 s |

These are acceptance thresholds, not a claim that the packaging machine or a single host can serve the stated population.

## Runtime acceptance

Engineering Admin can inspect:

`GET /api/v1/operations/production-certification?profile=30`

The runtime snapshot checks:

- multi-host topology health and failure-domain spread;
- authoritative PostgreSQL/evidence write safety;
- DB pool headroom;
- required-dependency availability from privacy-safe operational health samples;
- unresolved critical incidents.

Missing health history produces `CONDITIONAL`, not a false PASS. A failed runtime prerequisite produces `NO_GO`.

SLO state intentionally does not change `/api/v1/health/lb` eligibility by itself. A serving API is not removed from the load balancer merely because an error budget is burning; instead, new rollout/production acceptance is blocked.

## DB pool admission control

At critical connection-pool saturation, new mutating HTTP requests are rejected with HTTP 503 / `DB_POOL_SATURATED` and `Retry-After`. GET/read traffic is not fenced by this guard. The purpose is backpressure, not failover or authorization.

Default policy:

- warning ratio: 0.80;
- hard ratio: 0.95;
- profile 100 reference hard limit: 0.90;
- saturation guard can be configured through environment settings.

## Target-host evidence

Technical certification is evaluated from two operator-retained JSON inputs:

1. topology inventory (`mgc-multihost-topology-v1`);
2. measured acceptance evidence (`mgc-production-acceptance-evidence-v1`).

Required live evidence includes:

- sufficient HTTP request volume;
- HTTP p95 and error rate;
- dependency availability;
- maximum DB-pool saturation;
- consecutive external-LB probes;
- proof that non-idempotent request replay did not occur;
- host-loss drill;
- authoritative PostgreSQL failover drill;
- evidence-storage integrity after failover;
- measured RTO and RPO.

Example evidence under `ops/certification/` is explicitly marked `example_only=true` and must be replaced with measurements from the target environment.

## Commands

```bash
make production-certification-preflight

make production-certify \
  PROFILE=30 \
  TOPOLOGY=ops/multihost/topology.30.example.json \
  EVIDENCE=/secure/path/target-host-evidence.json
```

The certification report can return `GO`, `CONDITIONAL`, or `NO_GO`. Even `GO` contains `production_authorized=false` and `human_approval_required=true`.

After an approved change window, the separate deployment guard requires the exact confirmation token:

```bash
make production-deployment-guard \
  REPORT=production-certification.json \
  CONFIRM=APPROVED_CHANGE_WINDOW
```

The guard refuses any non-GO report and refuses reports that attempt to self-authorize production.

## Boundaries

v6.3.21 does not perform infrastructure fault injection, PostgreSQL promotion, STONITH, load generation, or human change approval. Those remain target-environment/operator responsibilities. Synthetic SQLite benchmarks remain CI diagnostics and are not accepted as production capacity evidence.
