# Verification — Окно в Китай Pilot v1.6.1

## Scope

Patch-релиз проверяет one-click deployment поверх функционального baseline v1.6.

## Passed package gates

- Security preflight: **11/11 PASS**
- Operations preflight: **15/15 PASS**
- Reliability preflight: **13/13 PASS**
- Governance preflight: **12/12 PASS**
- Business Operations preflight: **12/12 PASS**
- One-click deployment preflight: **26/26 PASS**
- TypeScript syntax (`tsc --noEmit --noCheck`): **PASS**
- One-click targeted tests: **2/2 PASS**
- Combined targeted pilot tests: **13/13 PASS**
- Bash syntax for start/stop/status launchers: **PASS**
- Simulated Linux Docker flow — fresh install: **PASS** (`.env → secrets → preflight → build → up → health → smoke → access file`)
- Simulated Linux upgrade flow — existing v1.6.0 `.env`: **PASS**, APP_VERSION migrated to `1.6.1-pilot`
- Simulated offline-image flow: **PASS**, `docker load → tag check → up --no-build`
- Simulated STOP/STATUS: **PASS**, named volume preserved and health reported
- SBOM generation: **878 npm components**

## Windows launcher verification boundary

PowerShell runtime is not installed in the packaging environment, so the Windows launcher cannot be executed here against an actual Windows Docker Desktop runtime. Static preflight verifies packaging, Docker commands, secure RNG usage, environment bootstrap, offline image path and health waiting. Actual Windows double-click smoke remains a target-host acceptance gate.

## External target gates

- real Docker image build/runtime smoke: **PENDING target host**;
- Windows Docker Desktop smoke: **PENDING Windows target**;
- online `npm audit` / image CVE scan: **PENDING network-enabled corporate CI**.

Package-level PASS does not claim these external gates have run.
