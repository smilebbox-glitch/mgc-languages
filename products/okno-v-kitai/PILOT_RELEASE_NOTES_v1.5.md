# «Окно в Китай» — Pilot v1.5

## Governance & Deployment Assurance

v1.5 развивает v1.4 без смены технологического стека. Основная цель релиза — сделать обновление, эксплуатационные политики и приёмку пилота воспроизводимыми и проверяемыми.

### Главное

- добавлен реестр SQLite migrations `schema_migrations`; текущая schema version — **2**;
- миграции идемпотентны и рассчитаны на upgrade существующей v1.4 БД без удаления данных;
- добавлен SQLite scheduler lock с TTL, исключающий параллельные refresh-runs;
- добавлены retention policies для source history, просроченных snapshots и архивного managed content;
- row cap source history теперь конфигурируется;
- добавлен Source SLA для `fx.aggregate` и `news.aggregate` по возрасту и quality score;
- SLA отображается в `/admin` и экспортируется в Prometheus;
- добавлен maintenance mode с пользовательским баннером; AI-analysis во время работ возвращает HTTP 503 + Retry-After;
- runtime config поднят до schema 2; backup schema 2 сохраняет source switches + maintenance state, но не секреты;
- restore остаётся совместимым со старыми runtime backup schema 1;
- managed content получил versioned export/import JSON bundle;
- import выполняет dry-run перед записью, лимитирован 1000 материалами / 1 МБ;
- добавлена конфигурационная validation-панель;
- retention/SLA остаются IT-owned env policies и не редактируются контентными ролями;
- добавлен автоматический IT Acceptance Report (`npm run pilot:acceptance`);
- package mode формирует статус CONDITIONAL; target + online mode может выдать ACCEPT только после runtime/CVE gates;
- Docker build после приложения запускает полный `tests/*.test.mjs`, поэтому image не собирается при реальном UI/build regression.

### Новые API

- `GET/PUT /api/admin/governance`
- `GET /api/admin/content-export`
- `POST /api/admin/content-import[?dryRun=1]`

### Новые ключевые параметры

- `SOURCE_HISTORY_RETENTION_DAYS=30`
- `SOURCE_HISTORY_MAX_ROWS=5000`
- `EXPIRED_SNAPSHOT_RETENTION_DAYS=7`
- `ARCHIVED_CONTENT_RETENTION_DAYS=365`
- `SCHEDULER_LOCK_TTL_SECONDS=120`
- `SOURCE_SLA_FX_SECONDS=1800`
- `SOURCE_SLA_FX_MIN_QUALITY=60`
- `SOURCE_SLA_NEWS_SECONDS=3600`
- `SOURCE_SLA_NEWS_MIN_QUALITY=50`

### Upgrade v1.4 → v1.5

1. Сделать SQLite backup (`npm run pilot:data-backup`) и вынести копию за пределы Docker volume.
2. Обновить `.env` новыми governance parameters.
3. Выполнить `docker compose build` — внутри build проходят preflight, application build и полный test-suite.
4. Выполнить `docker compose up -d`.
5. Проверить `/api/ready`: `migrationsPending` должен быть `0`.
6. В `/admin` проверить DB migrations, Source SLA и Configuration checks.
7. Запустить `ACCEPTANCE_MODE=target ONLINE_ACCEPTANCE=YES npm run pilot:acceptance` на хосте с доступом к Docker/registry.

### Ограничение пилота

SQLite и локальный rate limiter по-прежнему являются single-host/single-web-instance решениями. Для multi-host production потребуются корпоративная DB platform, distributed locking/rate limiting и внешний orchestration layer.
