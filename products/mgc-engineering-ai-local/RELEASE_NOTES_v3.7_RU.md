# MGC Engineering AI Local v3.7.0

## Основное

- Исправлена Docker-сборка: `docker compose build` теперь является штатной командой и использует корректные build contexts.
- Python/npm/system dependencies устанавливаются внутри Docker images; ручная установка пакетов на сервере не требуется.
- Добавлен `make start`: build + запуск выбранного CPU/GPU runtime после однократной настройки `.env`/SSO/model pins.
- Добавлен `scripts/build_preflight.py`, который проверяет build contexts и критичные входные файлы до запуска Docker BuildKit.
- Backend image выполняет `pip check` при сборке.
- Runtime дополнен системными библиотеками `libgomp1`, `libegl1`, `libopengl0` для ML/CAD стека.

## Engineering Compute Manager

- очереди `interactive`, `heavy`, `default`, `background`;
- Celery prefetch = 1;
- тяжёлый Design Review запускается асинхронно;
- UI показывает понятный статус и продолжает оставаться доступным во время расчёта;
- `ComputeJob` привязан к пользователю, поэтому результат очереди не раскрывается другому инженеру;
- фоновые sync-задачи получают более низкий приоритет.
