# Security Baseline — Pilot v1.6

v1.4 наследует v1.3 security controls и добавляет persistent data/scheduler controls.

## Identity / RBAC

- `viewer / editor / admin`;
- proxy identity доверяется только с `AUTH_PROXY_SECRET`;
- direct user access к app port не должен обходить reverse proxy;
- `ADMIN_API_TOKEN` — только pre-SSO механизм.

## Scheduler trust boundary

`/api/internal/refresh` принимает запрос только с `SCHEDULER_TOKEN`. Scheduler не публикует порт. Токен должен храниться как secret и отличаться от admin/SSO secrets.

Internal refresh делает loopback fetch к собственным API; это единственное сознательное исключение из правила `safeFetch` для server-side fetch. Внешний HTTP/HTTPS продолжает проходить через outbound allow-list.

## Persistent data

`/data` содержит runtime config, SQLite DB и audit. Root filesystem остаётся read-only.

SQLite не хранит env secrets. Managed content и source snapshots считаются внутренними корпоративными данными и должны попадать под backup/retention policy.

## Managed content

- editor/admin mutation endpoints защищены RBAC/rate limit;
- изменения аудируются;
- body ограничен по длине;
- UI рендерит текст, не raw HTML;
- archive используется вместо физического удаления в pilot flow.

## Audit / SIEM

Сохраняются correlation IDs, authorization denials, rate limit, outbound blocks, configuration changes, backup/restore и content updates. `AUDIT_HMAC_KEY` рекомендуется для controlled pilot.

## Supply chain

- deterministic lockfile;
- offline CycloneDX SBOM;
- `npm audit` online gate;
- optional Trivy/corporate image scanner.

## Known pilot limitations

- `node:sqlite` в Node 22 имеет experimental API status;
- SQLite — single-host pilot store, не HA shared DB;
- rate limit — in-process;
- scheduler — single instance без distributed leader election;
- local DB backup в том же volume не является DR без external copy.


## v1.5 governance security additions

- scheduler refresh защищён SQLite lock + TTL;
- maintenance state доступен для изменения только admin role;
- managed content import требует editor/admin и проходит size/schema validation + dry-run;
- retention/SLA policy не редактируется через UI и принадлежит IT configuration;
- configuration validation показывает blocking failures отдельно от warnings;
- Docker image build запускает полный test-suite после application build;
- runtime backup schema 2 по-прежнему исключает secrets.


## v1.6 privacy / user workspace additions

- SSO subject/e-mail не сохраняются в user business tables; ключ пользователя вычисляется через HMAC-SHA256.
- `USER_DATA_HMAC_KEY` является secret material и должен храниться в корпоративном secret store.
- disabled pilot-mode использует случайный HttpOnly `okno_device_id`; этот режим не предназначен для shared-browser сценариев.
- usage analytics в админке агрегирована; интерфейс не показывает историю конкретного пользователя.
- `USAGE_RETENTION_DAYS` ограничивает срок хранения telemetry; уведомления также очищаются scheduler.
- offline pack может содержать данные поездки пользователя, поэтому сотрудник должен хранить скачанный файл в соответствии с корпоративной политикой рабочего устройства.
- внешние notification channels в v1.6 отсутствуют, что исключает отправку пользовательских предпочтений во внешние мессенджеры/почту.
