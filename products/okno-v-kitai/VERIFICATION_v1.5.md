# Verification — Pilot v1.5

Дата проверки: 2026-09-06

## Package-level gates

- Security preflight: **11/11 PASS**
- Operations preflight: **15/15 PASS**
- Reliability preflight: **13/13 PASS**
- Governance preflight: **12/12 PASS**
- TypeScript syntax (`tsc --noEmit --noCheck`): **PASS**
- Targeted governance/operations/reliability tests: **8/8 PASS**
- Compose YAML parse: **PASS**
- Shell syntax (`bash -n scripts/*.sh`): **PASS**
- Top-level JSON parse: **PASS**
- CycloneDX SBOM generation: **PASS, 878 components**

## Upgrade test

Создана тестовая БД, имитирующая v1.4 без `schema_migrations`, с существующей записью managed content.

Результат после открытия v1.5:

- schema version: **2/2**;
- pending migrations: **0**;
- `scheduler_locks` создана;
- существующая запись `legacy` сохранена без изменения.

Статус: **PASS**.

## Full legacy UI/build tests

Прямой запуск `node --test tests/*.test.mjs` из source ZIP без установленного `node_modules` и без `dist/server` дал:

- 8 governance/operations/reliability tests — PASS;
- `rendered-html.test.mjs` — не стартует, так как `dist/server/index.js` появляется только после application build;
- `ui-components.test.mjs` — не стартует, так как source ZIP намеренно не содержит `node_modules/react`.

Это environment/pre-build limitation, а не отмеченный как PASS runtime gate. В v1.5 Dockerfile изменён: после `npm ci` и `npm run build` автоматически выполняется `node --test tests/*.test.mjs`; failure блокирует сборку image.

## Dependency vulnerability scan

`npm audit --audit-level=high --omit=dev` в текущей среде: **PENDING**.

Причина фактической попытки: `getaddrinfo EAI_AGAIN registry.npmjs.org`. Результат CVE scan не считается PASS.

## Docker runtime

Docker CLI/daemon в текущей рабочей среде отсутствует, поэтому `docker compose build`, runtime healthcheck и container smoke здесь не выдаются за пройденные.

Для корпоративной приёмки:

```bash
ACCEPTANCE_MODE=target ONLINE_ACCEPTANCE=YES npm run pilot:acceptance
```

Статус релиза до target execution: **CONDITIONAL / ready for controlled deployment verification**.

## Release hygiene

Перед packaging проверено отсутствие:

- `.env`;
- `node_modules`;
- `.sites-runtime` / npm cache;
- `.next` / `dist` build artifacts;
- SQLite runtime files;
- log files;
- PEM/private-key signatures;
- типичных hard-coded API-key signatures.

`FILE_MANIFEST_v1.5.sha256` покрывает **197 payload files** (сам manifest исключён из собственного списка).
