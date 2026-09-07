# MGC Engineering AI Local v6.0.4 — Performance, Scale & Load Certification

## Назначение

v6.0.4 — четвёртый шаг production-hardening. Версия не добавляет новый automotive-домен и не меняет ownership PLM/ERP/MES/QMS. Цель — сделать производительность измеримой и повторяемой перед корпоративным пилотом.

## Что добавлено

- три явных performance profile: CI / Pilot / Enterprise;
- capacity envelope для CPU/RAM host без ложного production-claim;
- 9 additive composite indexes для высоконагруженных read paths;
- deterministic synthetic CI benchmark;
- read-only HTTP load runner с bounded concurrency;
- p50/p95/p99, throughput и error-rate отчёт;
- performance preflight в `make verify`;
- performance pilot acceptance checklist;
- отдельные CI performance reports в `performance-reports/`.

## Критические read-path indexes

v6.0.4 добавляет индексы для:

1. BOM parent revision → children;
2. Digital Thread relationship subject traversal;
3. Digital Thread relationship object traversal;
4. project + VIN + build status;
5. build genealogy part/supplier/lot;
6. series quality project/time/part;
7. external integration object system/type/part;
8. integration ingest system/status/time;
9. canonical mapping project/type/status.

Миграция additive/idempotent и не меняет значения инженерных данных.

## Performance profiles

| Profile | Parts | BOM edges | VIN | Genealogy | Quality observations | Concurrent users target |
|---|---:|---:|---:|---:|---:|---:|
| CI | 5 000 | 25 000 | 2 000 | 20 000 | 50 000 | 4 |
| Pilot | 100 000 | 1 000 000 | 100 000 | 2 000 000 | 2 000 000 | 25 |
| Enterprise | 250 000 | 5 000 000 | 500 000 | 10 000 000 | 10 000 000 | 75 |

Pilot/Enterprise — target certification profiles. Они не считаются пройденными, пока не выполнены на целевом PostgreSQL/Redis/Qdrant runtime.

## CI benchmark, выполненный в packaging environment

Фактически выполнен synthetic SQLite run:

- 5 000 parts;
- 25 000 BOM edges;
- 2 000 VIN;
- 20 000 genealogy rows;
- 50 000 series quality observations.

Зафиксированный run:

- dataset load: ~431 ms;
- BOM children p95: ~1.67 ms;
- VIN genealogy p95: ~0.14 ms;
- 7-day series quality aggregation p95: ~45.85 ms.

Эти цифры подтверждают работу benchmark harness и индексов **только в CI-scale SQLite среде**. Они не являются заявленной производительностью корпоративной установки.

## Live-load safety

`scripts/http_load_test.py`:

- принимает только известные read-only GET path prefixes;
- ограничивает requests/concurrency;
- не запускает destructive/business transaction calls;
- сохраняет latency/error evidence в JSON;
- требует отдельного запуска на реальном pilot host.

## Начальные Pilot SLO gates

- ordinary read-only API p95 <= 500 ms;
- reconciliation p95 <= 10 s;
- HTTP error rate <= 1%;
- zero OOM/restart during steady-state certification;
- ACL/evidence fail-closed behaviour must remain correct under concurrent load.

Это engineering starting gates, а не универсальный отраслевой стандарт. Corporate IT/SRE может их ужесточить.

## Команды

```bash
make performance-preflight
make performance-ci
```

На запущенном controlled-pilot runtime:

```bash
python scripts/http_load_test.py \
  --base-url http://127.0.0.1:8080 \
  --path /api/v1/health/ready \
  --requests 1000 \
  --concurrency 25 \
  --profile pilot \
  --output performance-http-pilot.json
```

## Governance

Performance optimization не может отключать или ослаблять:

- Project/Area/Document ACL;
- provenance/evidence checks;
- source-of-truth conflict handling;
- quarantine/data-confidence rules;
- human approval boundaries.

Реальные Docker build, PostgreSQL load test, Redis/Qdrant load, Dockle image scan и production-shaped Pilot/Enterprise performance certification должны выполняться на approved corporate host.
