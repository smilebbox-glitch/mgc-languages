# Verification — MGC Engineering AI Local v6.3.31

## Release identity

- Application: **6.3.31**
- Database schema: **6.3.13**
- New DB migration: **none**
- Theme: **Resilience Drill Orchestration**
- Adjacent Rolling/Blue-Green compatibility: **6.3.30 ↔ 6.3.31**
- `production_authorized=false`

## Backend regression

The full backend suite was executed as four deterministic groups covering all test files:

- group 1: **166 PASS**;
- group 2: **145 PASS**;
- group 3: **177 PASS**;
- group 4: **164 PASS**;
- total: **652/652 PASS**;
- test files: **104/104**.

## Consolidated operational verification

`PYTHONPATH=backend python scripts/mgcctl.py verify --scope full --json`

Result: **24/24 stages PASS**. The scope includes security, architecture, rolling/blue-green, application HA, authoritative DB/evidence HA, multi-host topology, production/load/release certification, release provenance/trust, integration certification/runtime assurance, target-host assurance, incident evidence and resilience drill orchestration.

## v6.3.31 resilience-drill checks

- Resilience Drill preflight: **13/13 PASS**.
- Operations Consolidation: **32/32 PASS**.
- bounded catalog: 5 allowlisted scenarios;
- arbitrary shell injection: forbidden;
- live execution confirmation: exact `DRILL` token;
- mandatory recovery path: present;
- dependency faults in production: fail closed by default;
- production dependency override: maintenance-window reference required;
- simulation cannot produce `PASS`;
- incident-evidence binding copies hash + bounded codes only;
- no v6.3.31 DB migration.

## API / static integrity

- Python compileall: **PASS**.
- Shell syntax: **29/29 PASS**.
- Compose YAML parse: **19/19 PASS**.
- legacy method/path contracts: **181/181 preserved**;
- current bounded-context routes: **247**;
- legacy handler identity: preserved.

## Runtime-evidence boundary

A live fault-injection drill was **not** executed in this build environment. The release verifies orchestration, fail-closed policy, evidence integrity and simulation behavior. A live `PASS` evidence document can only be produced on a real permitted target Docker topology after actual fault injection, continuity observation and successful recovery.

## Supply chain

- provenance entries: **145/145 validated**;
- physically present source-package inputs: **138/145**;
- intentionally missing corporate build artifacts: **7** (`frontend/package-lock.json` plus Core/AI/Advanced Python lock + wheelhouse manifests);
- immutable image references configured in this build environment: **0/14**;
- offline OS-package bundle/install receipt: not present in this source build environment;
- status: **CONDITIONAL**;
- `production_authorized=false`.

These artifacts must be generated on the approved corporate build host/registry. No lock hash, image digest, OS receipt or CVE/SCA approval is fabricated by the source package.

## Package integrity

First independent ZIP→manifest pass after cache cleanup:

- controlled payload: **1046 files**;
- ZIP members including `BUILD_MANIFEST.json`: **1047**;
- duplicate members: **0**;
- missing / extra: **0 / 0**;
- size mismatch: **0**;
- SHA-256 payload mismatch: **0**;
- `__pycache__` / `.pytest_cache` / `.pyc` / `.pyo`: **0**;
- symlinks: **0**;
- `unzip -t`: **PASS**.

The package is rebuilt once more after this evidence is written; final external ZIP SHA-256 is recorded in the `.zip.sha256` sidecar.
