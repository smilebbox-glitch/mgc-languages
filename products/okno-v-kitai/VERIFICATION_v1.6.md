# Verification — Окно в Китай Pilot v1.6

Дата package verification: 2026-09-06.

## Итог

**Package status: CONDITIONAL — готов к controlled pilot после target/CI gates.**

Локально проверяемые security / operations / reliability / governance / business-operations gates проходят. Docker runtime smoke и online dependency vulnerability audit должны быть выполнены в корпоративной инфраструктуре.

## Пройденные проверки

- Security preflight: **11/11 PASS**.
- Operations preflight: **15/15 PASS**.
- Reliability preflight: **13/13 PASS**.
- Governance preflight: **12/12 PASS**.
- Business Operations preflight: **12/12 PASS**.
- Targeted Node tests: **11/11 PASS**.
- TypeScript parser (`tsc --noEmit --noCheck`): **PASS**.
- Shell syntax (`bash -n`): **PASS**.
- JSON parse: **PASS**.
- Compose YAML parse: **PASS**.
- SBOM generation: **PASS, 878 components**.
- SQLite v1.5 -> v1.6 migration simulation: **PASS**, schema `2 -> 3`, existing content preserved.
- Business schema smoke: **PASS** — preferences/favorites insert and notification `event_key` deduplication verified.
- User-data pseudonymization: HMAC-SHA256 layer packaged; raw SSO e-mail/subject are not written to user business tables.
- Controlled-pilot configuration: default/short `USER_DATA_HMAC_KEY` is a blocking configuration failure.

## v1.6 scope verified

- `/my` personal workspace.
- subscriptions by brand / market / topic / city / event.
- in-app notification generation after scheduler refresh.
- favorites on news and events.
- active personal trip persisted in SQLite.
- standalone HTML offline travel pack.
- usage telemetry with retention.
- aggregate `/api/admin/usage` dashboard without direct personal identifiers.
- schema migration v3 with `user_preferences`, `user_favorites`, `user_trips`, `user_notifications`, `usage_events`.

## Gates that remain external

### Docker build / runtime smoke — PENDING

Docker CLI/daemon is not available in the package-building environment. The project Dockerfile runs, in order, `npm ci`, `npm run pilot:preflight`, application build and the complete `tests/*.test.mjs` suite. Corporate target acceptance must additionally run `docker compose build`, `docker compose up -d` and `npm run pilot:smoke` / target acceptance.

### Dependency vulnerability audit — PENDING

`npm audit --audit-level=high --omit=dev` was attempted. npm could not reach `registry.npmjs.org` and returned `getaddrinfo EAI_AGAIN`. Therefore no claim is made that the dependency set is CVE-clean. Run `ONLINE_ACCEPTANCE=YES ACCEPTANCE_MODE=target npm run pilot:acceptance` in a network-enabled corporate CI environment.

## Privacy boundary

v1.6 notifications are in-app only. SMTP, Teams, Telegram Bot, mobile push and other external delivery channels are deliberately not part of this release. Offline travel pack may contain work-trip details and must be handled according to corporate endpoint/data policy.
