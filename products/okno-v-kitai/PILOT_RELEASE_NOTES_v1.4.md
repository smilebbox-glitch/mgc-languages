# Окно в Китай — Pilot v1.4
## Reliability & Content Operations

Дата релиза: 6 сентября 2026
Application version: `1.4.0-pilot`

## Цель релиза

v1.4 переводит внутренний пилот от process-local динамических данных к управляемому persistent data layer. Основной акцент: работоспособность при сбоях внешних источников, наблюдаемая свежесть данных и возможность менять корпоративный контент без rebuild.

## Новое

### Persistent SQLite

- `/data/okno.sqlite` в существующем named volume;
- WAL mode;
- `busy_timeout=5000`;
- автоматическое создание schema;
- таблицы `source_snapshots`, `source_history`, `content_items`.

### Persistent cache / graceful degradation

- FX и news используют SQLite snapshots;
- TTL и отдельное stale window;
- состояния `fresh / stale / expired`;
- при временном сбое используется последний валидный stale snapshot;
- FX умеет смешивать live часть с сохранённой stale частью вместо немедленного отката к жёстко заданным значениям;
- news при partial failure может дополнить live выдачу последним сохранённым набором.

### Source quality history

Сохраняются status, quality score, item count, latency, timestamp, error summary и hash агрегированного payload. История bounded до последних 5000 records.

### Scheduler

- второй container `china-auto-radar-scheduler`;
- старт после healthy web container;
- default interval 300 seconds;
- authenticated `POST /api/internal/refresh`;
- scheduler не публикует порт и не имеет persistent writable filesystem.

### Reliability dashboard

`/admin` показывает:

- SQLite state/path;
- scheduler configuration;
- cache snapshots;
- `FRESH / STALE / EXPIRED`;
- age и quality score;
- history quality;
- overall `WARMING_UP / HEALTHY / STALE / DEGRADED`.

### Managed content

- admin API для content items;
- статусы `draft / published / archived`;
- `editor` и `admin` могут изменять content;
- public API отдаёт только published items;
- `travel-guide` показывает корпоративные заметки без rebuild;
- изменения записываются в audit trail.

### Backup

- `npm run pilot:data-backup`;
- SQLite `VACUUM INTO` создаёт consistency snapshot в `/data/backups`;
- deployment guide содержит offline restore procedure и требование external DR copy.

### Monitoring

Prometheus дополнен cache state/age/quality gauges.

### Readiness

`/api/ready` теперь проверяет writable runtime data directory и доступность SQLite.

## Сохранено из v1.3

SSO-ready RBAC, trusted proxy secret, outbound allow-list, redirect validation, request IDs, rate limiting, audit hash chain/HMAC, runtime backup, SIEM-ready JSON logs, Prometheus, security headers, non-root/read-only Docker hardening, SBOM и online vulnerability gate.

## Осознанные границы

- `node:sqlite` в Node 22 имеет experimental API status;
- SQLite используется только как single-host pilot DB;
- scheduler single-instance, без distributed leader election;
- rate limiting in-process;
- local backup в том же volume не заменяет external DR backup;
- переход к HA/multi-host потребует PostgreSQL/shared DB и shared coordination layer.
