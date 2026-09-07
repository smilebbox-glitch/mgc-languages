# Окно в Китай — Pilot v1.6.1

Внутренняя информационная платформа для сотрудников компании, работающих с Китаем и китайским автопромом.

## Что есть в продукте

- новости и приоритетный мониторинг SHACMAN / GWM / отрасли;
- календарь автомобильных выставок и отраслевых событий;
- доказательный ИИ-анализ по собранным материалам;
- рыночный обзор;
- подготовка к командировке в Китай;
- CNY ↔ RUB: официальный курс ЦБ, конвертер и банковские наличные курсы;
- pilot admin control plane `/admin`.


## Pilot v1.6.1 — One-click Deployment

Patch-релиз v1.6.1 не меняет бизнес-функции v1.6 и добавляет нативный запуск без ручной подготовки конфигурации.

**Windows:** дважды нажмите `START.bat`.

**Linux / macOS:**

```bash
./start.sh
```

Launcher автоматически создаёт `.env`, генерирует pilot secrets, проверяет Docker/Compose, выполняет build + up, ждёт health/readiness, запускает smoke checks и создаёт локальный `.pilot-access.txt`. Для остановки и проверки состояния используются `STOP.bat` / `STATUS.bat` либо `./stop.sh` / `./status.sh`.

Если рядом лежит заранее собранный `okno-v-kitai-image.tar`, launcher использует `docker load` и стартует без обращения к npm registry. Подробности: `ONE_CLICK_DEPLOYMENT.md`.

## Pilot v1.6 — UX & Business Operations

v1.6 добавляет персональный рабочий контур сотрудника без новой внешней БД или очереди:

- `/my` — единый раздел подписок, уведомлений, избранного и активной командировки;
- подписки по SHACMAN/GWM, рынкам, темам, городам и конкретным мероприятиям;
- in-app notifications, которые scheduler формирует после обновления источников и дедуплицирует по event key;
- сохранение новостей и событий в избранное;
- персональная карточка поездки с маршрутом, датами, отелем, событием и заметками;
- автономный HTML `offline travel pack` с поездкой, последним FX snapshot, корпоративными памятками и избранным;
- page-view/business-event telemetry с retention policy;
- агрегированная usage analytics в `/admin` без ФИО/e-mail;
- пользовательский идентификатор хранится как HMAC-псевдоним; для controlled pilot `USER_DATA_HMAC_KEY` обязателен;
- SQLite migration v3 обновляет v1.5/v1.4 БД in-place.

Уведомления v1.6 — внутренние (in-app). E-mail/мессенджер push намеренно не включён в пилот, чтобы не добавлять новый канал обработки персональных данных без согласования IT/Security.

## Pilot v1.5 — Governance & Deployment Assurance

v1.5 добавляет поверх reliability-слоя v1.4 версионированные SQLite migrations, scheduler locking, retention policies, Source SLA, maintenance mode, managed-content import/export, configuration validation и автоматизированный IT acceptance report.

Ключевой принцип релиза: **никакой скрытой ручной приёмки**. Package gates, target runtime gates и online CVE gate разделены и явно отражаются в отчёте.

Быстрые команды:

```bash
npm run pilot:preflight
ACCEPTANCE_MODE=package npm run pilot:acceptance
# на целевом хосте после настройки .env и Docker:
ACCEPTANCE_MODE=target ONLINE_ACCEPTANCE=YES npm run pilot:acceptance
```

## Pilot v1.4 — Reliability & Content Operations

v1.4 сохраняет security/operations baseline v1.3 и добавляет слой управляемых данных:

- persistent SQLite database `/data/okno.sqlite` в Docker volume;
- WAL + busy timeout для устойчивой single-host работы;
- persistent cache для FX и новостей вместо process-memory cache;
- TTL + stale window + состояния `FRESH / STALE / EXPIRED`;
- graceful degradation: последний валидный snapshot используется при сбое внешнего источника;
- source history: status, latency, item count, quality score, last success;
- отдельный scheduler container для планового обновления источников;
- authenticated internal refresh endpoint;
- reliability dashboard в `/admin`;
- managed content: `draft / published / archived`, роли editor/admin;
- опубликованные корпоративные заметки выводятся в разделе «Перед поездкой» без пересборки приложения;
- SQLite online backup через `VACUUM INTO`;
- readiness теперь проверяет и writable `/data`, и доступность SQLite.

## Запуск

Для обычного pilot-mode ручное редактирование `.env` больше не требуется:

- Windows: `START.bat`;
- Linux/macOS: `./start.sh`.

Ручной IT-путь `host-preflight → docker compose build → up → smoke` сохранён и описан в `PILOT_DEPLOYMENT.md`. По умолчанию web доступен только на `127.0.0.1:3000`; корпоративный доступ через TLS/SSO reverse proxy настраивается IT отдельно.

## Основные endpoints

- `GET /api/health`
- `GET /api/ready`
- `GET /api/fx?city=kaluga|moskva`
- `GET /api/news`
- `POST /api/analyze`
- `GET /api/content?section=travel-guide`
- `GET /api/session`
- `GET /api/admin/status`
- `GET|PUT /api/admin/config`
- `GET /api/admin/reliability`
- `GET|POST|DELETE /api/admin/content`
- `GET /api/admin/audit?limit=50`
- `GET /api/admin/backup`
- `POST /api/admin/restore`
- `POST /api/internal/refresh` — только scheduler token
- `GET /api/metrics`

## Preflight

После `npm ci`:

```bash
npm run pilot:preflight
```

При доступе к npm advisory service:

```bash
npm run pilot:preflight:online
```

## Backup данных

В контейнере:

```bash
docker compose exec china-auto-radar npm run pilot:data-backup
```

Backup создаётся в `/data/backups`. Для реального DR скопируйте snapshot во внешнее корпоративное backup-хранилище; хранение копии только в том же Docker volume не защищает от потери volume/host.

Подробности: `PILOT_DEPLOYMENT.md`, `SECURITY_PILOT.md`, `PILOT_RELEASE_NOTES_v1.6.1.md`, `VERIFICATION_v1.6.1.md`, `ONE_CLICK_DEPLOYMENT.md`.
