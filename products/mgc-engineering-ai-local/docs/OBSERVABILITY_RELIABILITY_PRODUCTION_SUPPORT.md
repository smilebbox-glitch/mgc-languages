# Observability, Reliability & Production Support — v6.0.8

## Goal

v6.0.8 does not add an automotive business domain. It provides the operator layer needed to run MGC continuously: bounded-cardinality metrics, SLI/SLO evidence, queue/integration lag, incident evidence, support bundles and runbook-driven troubleshooting.

## SLI/SLO model

MGC distinguishes local application evidence from the authoritative multi-replica time-series system.

- `/metrics` exposes Prometheus-compatible counters/histograms/gauges.
- `OperationalHealthSample` stores only bounded dependency name/status/latency samples for local trend evidence.
- External Prometheus/OTel remains authoritative for multi-replica API availability and latency history.
- Error budget is explicit: target, observed good/total, bad events, allowed bad events and remaining ratio are all visible. There is no opaque reliability score.

Default policy:

- required dependency availability target: 99.5%;
- integration freshness compliance target: 95%;
- oldest queued compute-job warning threshold: 300 seconds;
- local health-sample retention: 30 days.

These defaults are deployment policy, not automotive requirements, and must be approved by corporate IT/SRE.

## Privacy / cardinality boundary

Prometheus labels must never include:

- user / employee id;
- VIN;
- part number;
- document id/name;
- raw query text;
- supplier or project free-text values.

HTTP metrics use bounded route templates, HTTP method and status class only. Integration labels use configured system code, which is a bounded administrator-defined set.

## Operational sampling

Set `OPERATIONAL_SAMPLING_ENABLED=true` to let Celery Beat capture readiness checks to the local health history. The sampler is not a replacement for Prometheus. If the sampler cannot reach a dependency it stores only `available/unavailable`, never endpoint URLs or exception text.

## Support bundle

Engineering Admin can export `/api/v1/operations/support-bundle`.

The bundle contains only:

- privacy-safe readiness snapshot;
- SLO/queue/integration summary;
- redacted incident summary;
- security posture;
- per-file SHA-256 manifest and ZIP SHA-256 response header.

It intentionally excludes raw application logs, request bodies, document content, queries, VIN/part browsing history, credentials and connector secret configuration.

## Human boundary

An incident, exhausted error budget or red readiness state is an operator signal. MGC does not restart infrastructure, fail over databases, close incidents or authorize production deployment automatically.

## Scheduler deployment

The v6.0.8 base and air-gap Compose stacks include a hardened Celery Beat service. In enterprise-security mode it uses the runtime PostgreSQL identity with `AUTO_MIGRATE_SCHEMA=false`; only the one-shot schema migration service has DDL authority. Set `OPERATIONAL_SAMPLING_ENABLED=true` to activate periodic health sampling. If disabled, Beat remains available for other approved schedules but the health-sampling entry is not registered.
