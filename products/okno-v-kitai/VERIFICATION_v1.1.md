# Verification — «Окно в Китай» Pilot v1.1

Дата: 06.09.2026

## Пройдено в текущей среде

- TypeScript/TSX syntax transpile: **91/91 PASS**.
- `lib/fx.ts` standalone TypeScript compile: **PASS**.
- CBR XML parser sample: **PASS**.
- Bank rate parser sample, включая повторное упоминание банка до таблицы: **PASS**.
- `compose.yaml` YAML parse: **PASS**.
- Compose hardening assertions (`read_only`, `cap_drop=ALL`, `/api/health`): **PASS**.
- Package metadata/version/start command: **PASS**.
- Diff against source archive: изменения ограничены валютным модулем, pilot hardening, конфигурацией и документацией.

## Ограничение среды проверки

Полный `npm test`/`vinext build` здесь не выполнен, потому что исходный архив не содержит `node_modules`, а рабочая среда не имеет сетевого доступа к npm registry. Это не требует ручной установки на целевом сервере: Dockerfile выполняет `npm ci` во время `docker compose build`.

## Обязательная проверка на целевом сервере

```bash
docker compose build --pull
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:${APP_PORT:-3000}/api/health
curl -fsS http://127.0.0.1:${APP_PORT:-3000}/api/ready
curl -fsS 'http://127.0.0.1:'${APP_PORT:-3000}'/api/fx?city=kaluga'
```

После этого открыть раздел «Перед поездкой» и проверить переключение Калуга/Москва, конвертацию CNY↔RUB и live/fallback статус.
