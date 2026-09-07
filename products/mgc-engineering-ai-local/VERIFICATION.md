# MGC Engineering AI Local v6.3.34 - Verification

Application: **6.3.34**  
Database schema: **6.3.13**  
Migration: **none**

## Release scope

v6.3.34 introduces **Multi-Vehicle Product Applicability** on the existing `VehicleVariant` + `ConfigurationApplicability` model. Passenger Car, LCV, Truck, Bus, Special Vehicle and Component programs share one engineering Digital Thread; configuration differences are explicit variant attributes/applicability, not separate product databases.

## Functional / regression verification

- backend regression: **686/686 PASS**;
- backend test files: **107/107**;
- full `mgcctl verify --scope full --json`: **27/27 PASS**;
- multi-vehicle applicability preflight: **14/14 PASS**;
- pilot-readiness preflight: **16/16 PASS**;
- API contract preflight: **5/5 PASS**;
- legacy API baseline: **181/181 preserved**;
- current API routes: **247**;
- no new multi-vehicle API route required;
- DB schema remains **6.3.13**, no migration.

Full verification scopes:

1. docker-security
2. compose-security
3. api-access
4. enterprise-security
5. secret-scan
6. architecture
7. contexts
8. ports-adapters
9. domain-integrity
10. rolling
11. blue-green
12. ha
13. authoritative-ha
14. multi-host
15. production-certification
16. load-certification
17. release-acceptance
18. release-provenance
19. external-trust
20. integration-certification
21. integration-runtime-assurance
22. target-host-assurance
23. incident-evidence
24. resilience-drill
25. resilience-certification
26. pilot-readiness
27. multi-vehicle-applicability

## Multi-vehicle verification

The release verifies:

- canonical vehicle classes: passenger car / LCV / truck / bus / special vehicle / component;
- passenger and truck schema acceptance;
- invalid vehicle class and out-of-bounds configuration rejection;
- canonical profile merge without losing custom attributes;
- bounded wheelbase/GVW/payload/battery values;
- normalized vehicle configuration serialization;
- workspace class counts / multi-vehicle posture;
- passenger/commercial vehicle UI fields;
- two synthetic demo programs (`DEMO-PASSENGER`, `DEMO-TRUCK`);
- no DB migration;
- explicit applicability; UNKNOWN is not treated as applies-to-all.

## Static verification

- Python `compileall`: **PASS**;
- shell syntax: **33/33 PASS**;
- Compose YAML parse: **20/20 PASS** (includes demo-ready overlay);
- API legacy contract: **181/181 preserved**;
- current routes: **247**.

## Upgrade / rollback

- application: **6.3.34**;
- schema: **6.3.13**;
- adjacent rolling/blue-green window: **6.3.33 <-> 6.3.34**;
- new workers accept the adjacent previous-release task envelope where rolling compatibility requires it;
- resilience recovery baseline for a production-grade v6.3.34 certification must be the approved adjacent **v6.3.33** baseline;
- emergency rollback remains independent of the new product-applicability feature.

## Supply-chain posture

After final verification is part of the source tree:

- `BUILD_INPUTS` provenance entries: **164/164 validated**;
- source-package build-input files present: **157/164**;
- expected missing corporate artifacts: **7**;
- immutable corporate image references populated in this packaging environment: **0/14**;
- SBOM: **37 declared components**;
- supply-chain status: **CONDITIONAL**;
- `production_authorized=false`.

The seven intentionally absent corporate build artifacts are:

1. `frontend/package-lock.json`
2. `backend/locks/requirements-core.lock.txt`
3. `backend/wheelhouse/core/WHEELHOUSE_MANIFEST.json`
4. `backend/locks/requirements-ai.lock.txt`
5. `backend/wheelhouse/ai/WHEELHOUSE_MANIFEST.json`
6. `backend/locks/requirements-advanced.lock.txt`
7. `backend/wheelhouse/advanced/WHEELHOUSE_MANIFEST.json`

The compatibility supply-chain preflight remains **27/27 PASS** and strict mode fails closed while approved corporate locks/digests are unavailable.

## Environment limitation

The packaging environment does not provide an approved corporate Docker build/runtime path with immutable image digests and CVE/SCA receipts. Therefore this verification does **not** claim a corporate image build, real target-host deployment, real PLM/ERP/MES/QMS integration, homologation approval, or production authorization. Those remain controlled IT/pilot acceptance steps.

## Release package integrity

First independent archive pass on the frozen release tree:

- controlled payload files: **1095**;
- ZIP members including embedded `BUILD_MANIFEST.json`: **1096**;
- duplicate members: **0**;
- missing files: **0**;
- extra files: **0**;
- size mismatches: **0**;
- SHA-256 mismatches: **0**;
- cache/bytecode artifacts: **0**;
- symlinks: **0**;
- ZIP CRC: **PASS**.

`BUILD_MANIFEST.json` is intentionally excluded from its own hash inventory and is included as the 1096th ZIP member. The final release ZIP is rebuilt after these evidence lines and the final `BUILD_INPUTS` regeneration, then independently rechecked before distribution.
