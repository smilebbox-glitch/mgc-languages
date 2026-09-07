# Verification — Окно в Китай Pilot v1.4

Дата: 6 сентября 2026
Версия: `1.4.0-pilot`

## PASS — package-level gates

- `npm run pilot:security`: **11/11 PASS**.
- `npm run pilot:operations`: **15/15 PASS**.
- `npm run pilot:reliability`: **13/13 PASS**.
- targeted Node tests: **6/6 PASS**.
- `npm run pilot:syntax` (`tsc --noEmit --noCheck`): **PASS**.
- полный `npm run pilot:preflight`: **PASS**.
- MJS syntax: **6 scripts PASS**.
- shell syntax: **PASS**.
- JSON parse (`package.json`, lockfile, SBOM, components, hosting config): **PASS**.
- Compose parse: **PASS**, services `china-auto-radar` + `china-auto-radar-scheduler`.
- common hard-coded secret signature scan: **PASS**.
- source package excludes `.env`, `node_modules`, `dist`: **PASS**.
- Node runtime SQLite capability smoke: **PASS**.
- SQLite WAL write/read smoke: **PASS**.
- SQLite `VACUUM INTO` backup smoke: **PASS**.
- CycloneDX SBOM generation: **PASS — 878 npm components**.

## Important distinction: parser vs full typecheck

A raw `tsc --noEmit` was also attempted in the unpacked source environment. It is **not a valid typecheck result here**, because the source release intentionally contains no `node_modules`; TypeScript therefore cannot resolve React/Next/@types/node and other declared packages. This is recorded as environment-limited, not PASS. The target Docker build starts with `npm ci` and then executes the application preflight/build.

## PENDING — target/online gates

### Dependency vulnerability advisory

`npm run pilot:audit-deps` attempted on 6 September 2026 but npm could not reach `registry.npmjs.org`:

`getaddrinfo EAI_AGAIN registry.npmjs.org`

Therefore no claim is made that dependency CVE audit is clean. Corporate CI must run the included online gate.

### Docker build / runtime smoke

The current verification environment does not provide a Docker CLI/daemon (`docker: command not found`). Therefore the following remain mandatory on the target host/CI:

1. `bash scripts/host-preflight.sh`
2. `docker compose build`
3. `docker compose up -d`
4. `bash scripts/container-smoke.sh`
5. confirm both web and scheduler containers remain running
6. confirm `/api/ready` reports SQLite available
7. confirm scheduler warms snapshots and `/admin` reaches `HEALTHY`
8. perform a controlled stale-source degradation test
9. perform SQLite backup + restore drill on a test environment
10. run online dependency/image vulnerability scanner

## Security note

All external server-side HTTP remains centralized through `safeFetch`. The only direct server-side fetch exception is the authenticated internal refresh orchestrator calling the application's own loopback API; it is explicitly checked by the security preflight and is not an external network bypass.
