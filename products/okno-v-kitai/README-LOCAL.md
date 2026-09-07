# Окно в Китай — локальный запуск Pilot v1.6.1

## Самый простой запуск

### Windows

Дважды нажмите `START.bat`.

### Linux / macOS

```bash
./start.sh
```

Первый запуск сам создаёт `.env`, генерирует обязательные secrets, собирает image, запускает web + scheduler и ждёт readiness. Данные администратора сохраняются локально в `.pilot-access.txt`.

`STOP.bat` / `./stop.sh` останавливает сервис без удаления persistent volume. `STATUS.bat` / `./status.sh` показывает состояние.

---

## 1. Ручная подготовка для IT

```bash
cp .env.example .env
```

Для controlled pilot замените как минимум:

- `ADMIN_API_TOKEN` — если SSO ещё не подключён;
- `AUDIT_HMAC_KEY`;
- `SCHEDULER_TOKEN`.

## 2. Ручная проверка хоста

```bash
bash scripts/host-preflight.sh
```

## 3. Ручная сборка и запуск

```bash
docker compose build
docker compose up -d
docker compose ps
bash scripts/container-smoke.sh
```

Поднимаются два сервиса:

- `china-auto-radar` — web/API;
- `china-auto-radar-scheduler` — плановое обновление FX/news.

## 4. Данные

Named volume `okno-runtime-data` содержит:

- `/data/runtime-config.json`;
- `/data/okno.sqlite` + WAL/SHM;
- `/data/audit/audit.jsonl`;
- `/data/backups/*` после запуска backup-команды.

Удаление контейнера не удаляет данные. `docker compose down -v` удаляет volume и данные — использовать только осознанно.

## 5. Admin

`/admin` показывает источники, audit, reliability snapshots/history и managed content. В `AUTH_MODE=disabled` admin/editor операции доступны по `ADMIN_API_TOKEN`; в `AUTH_MODE=proxy` права приходят из SSO-групп.


## v1.6 acceptance

Локально: `ACCEPTANCE_MODE=package npm run pilot:acceptance`. На корпоративном сервере после deployment: `ACCEPTANCE_MODE=target ONLINE_ACCEPTANCE=YES npm run pilot:acceptance`.

## v1.6 personal workspace

После запуска откройте `/my`. Для controlled pilot обязательно задайте `USER_DATA_HMAC_KEY` длиной не менее 32 символов. В AUTH_MODE=proxy пользовательский профиль привязывается к SSO subject; в disabled pilot-mode — к HttpOnly device cookie текущего браузера.
