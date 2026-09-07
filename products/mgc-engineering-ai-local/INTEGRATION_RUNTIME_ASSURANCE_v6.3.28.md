# MGC Engineering AI Local v6.3.28 — Integration Runtime Assurance

## Scope

v6.3.28 hardens the v6.3.27 PLM/PDM/ERP/MES/QMS integration certification layer for production runtime behavior. It does not add source-system writeback, does not change source-of-truth ownership and does not introduce a database migration.

Application version: **6.3.28**  
Database schema: **6.3.13**  
Database migration: **none**

## Bounded cache staleness

`runtime_posture` now reports `mgc.integration-runtime-posture.v2` and evaluates the newest locally cached external object against `max_cache_staleness_minutes`.

- default bound: `max(2 × expected_freshness_minutes, 60 minutes)`;
- explicit contract bound must be `> 0` and `<= 10080` minutes;
- a failed source with fresh cache may serve **DEGRADED_READ_ONLY**;
- a failed source with stale cache is **BLOCKED** for cached engineering reads;
- a healthy source with stale cache is **DEGRADED_READ_ONLY** until refresh;
- raw external IDs are not exposed by runtime posture.

## Recovery sync guard

A stale/failed integration can otherwise deadlock if the sync endpoint is blocked by the same degraded posture it is meant to recover. v6.3.28 adds an explicit, backward-compatible recovery gate:

- `recovery_sync_enabled=false` by default for existing configurations;
- v6.3.28 reference contracts opt in with `recovery_sync_enabled=true`;
- recovery pulls are allowed only when degradation reasons are limited to source-health/cache-availability/cache-staleness conditions;
- quarantine, low-success-rate and certification degradation remain fail-closed;
- authoritative source mutation remains forbidden.

## Reliability accounting correction

Integration sync code records a successful run as `status="ok"`. v6.3.27 runtime reliability calculation omitted `ok` from its success set. v6.3.28 counts `ok`, `completed` and `success` as successful terminal states when `failed_count == 0`, preventing false degradation of healthy integrations.

## Reference contracts

PLM, PDM, ERP, MES and QMS example contracts now declare both:

- bounded `max_cache_staleness_minutes` derived from each source freshness target;
- `recovery_sync_enabled=true` for the new certified reference profile.

Existing customer configurations do not acquire recovery sync implicitly.

## Production boundary

This release certifies software behavior and local contract/preflight evidence. A real Teamcenter/Windchill/3DEXPERIENCE/SAP/MES/QMS connection still requires target-host TLS/authentication/network evidence, representative reconciliation and human release approval. `production_authorized=false` remains the default.
