# MGC Engineering AI Local v6.0.4 — Performance, Scale & Load Certification

## Purpose

v6.0.4 does not add a new engineering domain. It adds a repeatable certification harness for capacity, query/index readiness and read-only HTTP load testing. Results from a packaging/CI container are **not** enterprise performance claims.

## Profiles

| Profile | Parts | BOM edges | VINs | Genealogy rows | Quality observations | Concurrent users |
|---|---:|---:|---:|---:|---:|---:|
| CI | 5k | 25k | 2k | 20k | 50k | 4 |
| Pilot | 100k | 1m | 100k | 2m | 2m | 25 |
| Enterprise | 250k | 5m | 500k | 10m | 10m | 75 |

CI uses an ephemeral SQLite synthetic dataset only to verify the benchmark/index harness. Pilot and Enterprise certification must run on the target PostgreSQL/Redis/Qdrant topology.

## SLO starting gates

- ordinary read-only API p95: <= 500 ms for Pilot, <= 750 ms for Enterprise;
- reconciliation p95: <= 10 s for Pilot, <= 20 s for Enterprise;
- HTTP error rate: <= 1%;
- zero OOM kills/restarts during steady-state certification;
- required-source reconciliation remains fail-closed under load;
- CPU-only host must retain operating-system/database reserve capacity.

These are starting engineering acceptance gates, not universal automotive standards. Corporate SRE/IT owners may tighten them.

## Critical composite indexes

v6.0.4 adds additive indexes for high-cardinality paths:

- BOM parent revision -> children;
- deterministic relationship subject/object traversal;
- project + VIN build lookup;
- build genealogy part/supplier/lot lookup;
- series-quality project/time/part aggregation;
- external integration object lookup;
- ingest quarantine/status scan;
- canonical mapping project/type/status scan.

## Commands

```bash
make performance-preflight
make performance-ci
```

On a running controlled-pilot API:

```bash
python scripts/http_load_test.py \
  --base-url http://127.0.0.1:8080 \
  --path /api/v1/health/ready \
  --requests 1000 \
  --concurrency 25 \
  --profile pilot \
  --output performance-http-pilot.json
```

For an authenticated project endpoint, provide `--api-key` only through a protected shell/runtime secret. Do not commit credentials into benchmark reports.

## Required live certification sequence

1. Restore a sanitized production-shaped snapshot or generate an approved synthetic corporate dataset.
2. Run PostgreSQL `ANALYZE` after loading.
3. Capture `EXPLAIN (ANALYZE, BUFFERS)` for the slowest BOM, VIN, quality and reconciliation queries.
4. Run warm-up traffic before measuring p50/p95/p99.
5. Run steady-state and burst tests separately.
6. Record API latency, DB CPU, DB connections, Redis memory, worker queue depth, Qdrant latency, host CPU/RAM and container restarts.
7. Repeat with local LLM disabled and enabled; deterministic engineering core must remain usable when inference is slow/unavailable.
8. Keep reports as release evidence; do not tune away ACL or evidence checks to hit SLOs.

## Governance

- no destructive load endpoints;
- no load testing against live production without IT/SRE approval;
- no automatic index drops or query-plan changes;
- no SLO pass based only on this packaging environment;
- performance optimizations may not weaken ACL, provenance, human approval or evidence fail-closed rules.
