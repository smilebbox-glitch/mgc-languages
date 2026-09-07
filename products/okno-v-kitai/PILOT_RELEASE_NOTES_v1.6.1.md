# Окно в Китай — Pilot v1.6.1

## One-click Deployment Patch

v1.6.1 — patch поверх Pilot v1.6. Бизнес-функции, SQLite schema v3, RBAC, governance и privacy-модель не меняются.

### Добавлено

- `START.bat` для двойного клика в Windows;
- `start.sh` для Linux/macOS;
- `STOP.bat` / `stop.sh`;
- `STATUS.bat` / `status.sh`;
- PowerShell 5.1-compatible Windows launcher без внешних модулей;
- автоматическое создание `.env` из `.env.example`;
- криптографическая генерация `ADMIN_API_TOKEN`, `SCHEDULER_TOKEN`, `USER_DATA_HMAC_KEY`, `AUDIT_HMAC_KEY` для базового pilot-mode;
- сохранение локальных данных доступа в `.pilot-access.txt` с исключением файла из Git/Docker context;
- автоматическая проверка Docker/Compose и попытка запуска Docker Desktop на Windows/macOS;
- Compose validation, build/up, ожидание `healthy`, smoke checks и автоматическое открытие UI;
- offline image path: `okno-v-kitai-image.tar → docker load → up --no-build`;
- отдельный `pilot:oneclick` preflight, включённый в общий `pilot:preflight`;
- targeted tests one-click packaging;
- SBOM/acceptance генераторы теперь используют текущую patch-version автоматически.

### Security boundaries

- launcher не переводит bind на `0.0.0.0` автоматически;
- `APP_BIND_ADDRESS=0.0.0.0` требует явного `ALLOW_PUBLIC_BIND=YES`;
- при уже настроенном `AUTH_MODE=proxy` launcher не генерирует неизвестный reverse-proxy secret и требует корректный `AUTH_PROXY_SECRET`;
- существующий `.env` не заменяется шаблоном;
- `STOP` сохраняет named volume и пользовательские данные.

### Air-gapped / restricted network

Обычный первый build требует доступ к npm registry либо корпоративному npm proxy. Для закрытого контура IT может заранее предоставить Docker image tar с ожидаемым тегом; one-click launcher использует его без build.
