# «Окно в Китай» — Deployment Blueprint Pilot v1.6.1

## 0. One-click pilot deployment

После однократной установки Docker базовый pilot-mode запускается без ручной установки Node.js/npm и без ручного заполнения `.env`:

- Windows: `START.bat`;
- Linux/macOS: `./start.sh`.

Launcher создаёт `.env` только если его нет, генерирует обязательные случайные secrets, не перезаписывает уже настроенный SSO-mode, валидирует Compose, собирает/запускает два сервиса, ждёт Docker healthcheck и выполняет smoke checks. Генерируемые `.env` и `.pilot-access.txt` исключены из Git и Docker build context.

Offline/закрытый контур: если IT разместил в корне `okno-v-kitai-image.tar` с image `okno-v-kitai:1.6.1-pilot`, launcher выполняет `docker load` и `docker compose up -d --no-build`.

One-click не заменяет инфраструктурные действия IT для корпоративного TLS, DNS, SSO, firewall и external backup.

## 1. Целевая схема

`Сотрудник → corporate DNS/TLS/SSO reverse proxy → localhost:3000 → web/API container → allow-listed HTTPS sources`

Плановое обновление:

`Scheduler container → authenticated /api/internal/refresh → FX/news refresh → SQLite snapshots/history`

Persistent state:

`Docker volume /data → runtime-config.json + okno.sqlite + audit.jsonl + local backup snapshots`

## 2. Минимальные требования

- Linux x86_64;
- Docker Engine 24+ и Compose v2;
- рекомендовано 2 vCPU, 2 GB RAM, 5 GB свободного места;
- корпоративные DNS/NTP;
- исходящий HTTPS к согласованным источникам;
- TLS/SSO на reverse proxy.

Node runtime в образе: Node 22. В v1.4 используется встроенный `node:sqlite`; в Node 22 API имеет experimental status, поэтому это сознательный выбор для single-host pilot. Для production-scale/multi-host следующий шаг — PostgreSQL или корпоративная DB platform.

## 3. Секреты

Pre-SSO минимум:

```bash
openssl rand -hex 32  # ADMIN_API_TOKEN
openssl rand -hex 32  # AUDIT_HMAC_KEY
openssl rand -hex 32  # SCHEDULER_TOKEN
```

SSO mode:

```env
AUTH_MODE=proxy
AUTH_PROXY_SECRET=<secret-manager-value>
AUTH_ADMIN_GROUP=okno-china-admin
AUTH_EDITOR_GROUP=okno-china-editor
ADMIN_API_TOKEN=
AUDIT_HMAC_KEY=<secret-manager-value>
SCHEDULER_TOKEN=<secret-manager-value>
```

## 4. Сборка и запуск

```bash
cp .env.example .env
bash scripts/host-preflight.sh
docker compose build
docker compose up -d
docker compose ps
bash scripts/container-smoke.sh
```

Docker build выполняет `npm run pilot:preflight`. Online CVE advisory check остаётся CI gate.

## 5. Контейнеры

### `china-auto-radar`

Web/API, RBAC, outbound policy, SQLite access, audit, metrics.

### `china-auto-radar-scheduler`

Отдельный process/container того же image. Каждые `SCHEDULER_INTERVAL_SECONDS` вызывает authenticated refresh orchestration. Он не публикует порт и не имеет writable persistent filesystem.

Scheduler token даёт право только на internal refresh; всё равно замените default token перед пилотом.

## 6. Persistent database

Путь: `/data/okno.sqlite`.

Таблицы v1.4:

- `source_snapshots` — последняя пригодная версия данных с TTL/stale window;
- `source_history` — история запусков и качество источников;
- `content_items` — управляемый корпоративный контент.

SQLite включён в WAL mode с `busy_timeout=5000`. Это подходит для single-host pilot с одним web writer. Это не HA database architecture.

## 7. Cache / graceful degradation

FX defaults:

- TTL: `FX_CACHE_TTL_SECONDS=900`;
- stale window: `FX_CACHE_STALE_SECONDS=86400`.

News defaults:

- TTL: `NEWS_CACHE_TTL_SECONDS=900`;
- stale window: `NEWS_CACHE_STALE_SECONDS=21600`.

Поведение:

1. `FRESH` snapshot отдаётся без внешнего запроса.
2. После TTL приложение/scheduler пытается получить live data.
3. При сбое используется последний `STALE` snapshot в допустимом stale window.
4. После `stale_until` snapshot имеет `EXPIRED` и не используется как доверенный fallback.
5. Если валидного snapshot ещё не было, для FX остаётся статический emergency fallback; новости могут вернуться пустыми без падения всего UI.

## 8. Source quality

Для запусков сохраняются:

- source key / scope;
- status;
- quality score 0–100;
- item count;
- latency;
- timestamp;
- error summary;
- payload hash для агрегированных snapshots.

История ограничена последними 5000 записями, чтобы pilot DB не росла бесконтрольно.

`/admin` показывает overall state `WARMING_UP / HEALTHY / STALE / DEGRADED` и состояние snapshots.

## 9. Managed content

Роли:

- viewer — читает опубликованные материалы;
- editor — создаёт/редактирует `draft/published/archived`;
- admin — editor + operations/security control plane.

Материалы `section=travel-guide` автоматически появляются в «Перед поездкой». React выводит body как текст, без HTML injection.

Изменения контента записываются в audit trail.

## 10. Backup / restore database

Консистентный local snapshot:

```bash
docker compose exec china-auto-radar npm run pilot:data-backup
```

Команда использует SQLite `VACUUM INTO` и создаёт `/data/backups/okno-<timestamp>.sqlite`.

Для DR выгрузите backup за пределы volume, например через корпоративный backup agent или `docker cp`.

Offline restore пример:

```bash
docker compose stop china-auto-radar-scheduler china-auto-radar
docker compose run --rm --no-deps --entrypoint sh china-auto-radar -lc \
  'rm -f /data/okno.sqlite-wal /data/okno.sqlite-shm && cp /data/backups/<backup>.sqlite /data/okno.sqlite'
docker compose up -d
bash scripts/container-smoke.sh
```

Перед restore обязательно сохраните текущую БД отдельно. Для production используйте корпоративную backup/retention policy и периодический restore drill.

## 11. SSO / RBAC

Reverse proxy после успешной SSO-аутентификации передаёт:

- `X-Forwarded-User`;
- `X-Forwarded-Email`;
- `X-Forwarded-Groups`;
- `X-Okno-Proxy-Secret`;
- `X-Request-ID`.

Client-supplied значения должны удаляться и заменяться proxy.

## 12. Security baseline

Сохранено из v1.3:

- localhost bind;
- non-root;
- read-only root filesystem;
- `no-new-privileges`;
- `cap_drop: ALL`;
- CPU/RAM/PID limits;
- rate limiting;
- outbound allow-list + redirect validation;
- structured security logs;
- append-only audit hash chain/HMAC;
- Prometheus endpoint;
- SBOM + online vulnerability gate.

Единственное прямое server-side `fetch()` вне `safeFetch` — контролируемый loopback `/api/internal/refresh → собственный localhost API`; он не используется для внешнего трафика и требует scheduler secret.

## 13. Health / readiness

- `/api/health` — web process жив;
- `/api/ready` — `/data` writable и SQLite доступна;
- scheduler стартует только после healthy web service;
- внешние FX/news/RAG не являются startup dependency.

## 14. Pilot acceptance

1. host preflight PASS;
2. Docker build PASS после `npm ci`;
3. два сервиса находятся в running state;
4. web healthy;
5. `/api/ready` показывает SQLite available;
6. scheduler создаёт snapshots;
7. `/admin` показывает `HEALTHY` после успешного warm-up;
8. остановка внешнего FX/news источника приводит к `STALE`, но не к падению UI;
9. после stale window данные становятся `EXPIRED`;
10. content editor публикует заметку без rebuild;
11. изменение появляется в audit;
12. SQLite backup создаётся и копируется во внешнее backup-хранилище;
13. restore drill выполняется на тестовой среде;
14. SSO/RBAC и direct-port isolation подтверждены;
15. online CVE/image scan проходит в corporate CI.

## 15. Граница v1.4

Это production-oriented single-host internal pilot. До масштабирования: PostgreSQL/shared DB, distributed scheduler/leader election, shared rate limiting, HA ingress, corporate secrets manager, centralized audit retention, image signing/provenance, formal threat model/pentest и DR automation.


## 16. Governance v1.5

### Database migrations

`getPilotDb()` автоматически применяет недостающие migrations в транзакции `BEGIN IMMEDIATE`. `/api/ready` не считается ready, если `migrationsPending > 0`. Перед upgrade обязательна внешняя копия SQLite backup.

### Scheduler locking

Refresh использует SQLite lock `source-refresh`. `SCHEDULER_LOCK_TTL_SECONDS` должен быть меньше обычного `SCHEDULER_INTERVAL_SECONDS`. Повторный scheduler-run при активном lock завершается как `skipped: lock-held`, не создавая второй набор внешних запросов.

### Retention

Retention выполняется scheduler после refresh. Значения задаются IT через env. Удаление архивного managed content можно фактически отключить значением `ARCHIVED_CONTENT_RETENTION_DAYS=0`.

### Maintenance

Maintenance управляется admin через `/admin`, сохраняется в runtime config schema 2 и входит в runtime backup. Пользовательский UI продолжает отдавать read-only данные; expensive AI POST блокируется HTTP 503.

### Managed content portability

Export/import JSON не содержит application secrets. Перед import UI выполняет dry-run. Все фактические import/export операции пишутся в audit trail.

## 17. IT Acceptance

Package report:

```bash
ACCEPTANCE_MODE=package npm run pilot:acceptance
```

Target acceptance после настройки `.env` и запуска сервисов:

```bash
ACCEPTANCE_MODE=target ONLINE_ACCEPTANCE=YES npm run pilot:acceptance
```

`ACCEPT` допустим только при прохождении target runtime gates и online vulnerability audit. Без них report остаётся `CONDITIONAL`. Отчёты сохраняются в `acceptance/`.


## 17. Business Operations v1.6

### Privacy key

Для controlled pilot задайте `USER_DATA_HMAC_KEY` как отдельный случайный секрет (>=32 символов). Не используйте default из `.env.example`. Host preflight блокирует запуск с default/коротким ключом. При ротации этого ключа существующие пользовательские профили становятся логически недоступными, поэтому ротацию выполняйте как управляемую миграцию, а не ad-hoc изменение.

### User data

SQLite v3 хранит HMAC-псевдоним, подписки, избранное, активную поездку, in-app уведомления и usage events. E-mail и ФИО в эти таблицы не записываются. `USAGE_RETENTION_DAYS` по умолчанию 90 дней; scheduler применяет cleanup автоматически.

### Notifications

Scheduler после source refresh создаёт дедуплицированные in-app уведомления по брендам/рынкам/темам и предстоящим мероприятиям. В v1.6 нет SMTP, Teams, Telegram Bot или push-интеграции — такие каналы добавляются только после отдельного security/privacy review.

### Offline pack

`GET /api/user/offline-pack` формирует автономный HTML на момент запроса. Это snapshot, а не источник истины: перед обменом валюты, поездкой или регистрацией сотрудник должен перепроверять изменяемые условия.

### Usage analytics

`/api/admin/usage` доступен admin и возвращает агрегаты по событиям/страницам и числу HMAC-псевдонимов. Для расширенной BI-интеграции используйте агрегированный экспорт, а не raw user events.
