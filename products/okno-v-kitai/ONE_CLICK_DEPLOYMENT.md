# Окно в Китай — one-click запуск

## Windows

1. Один раз установите Docker Desktop.
2. Распакуйте релиз.
3. Дважды нажмите **START.bat**.

При первом запуске launcher сам:
- проверит Docker и попытается запустить Docker Desktop;
- создаст `.env` из `.env.example`, если файла ещё нет;
- сгенерирует криптографически случайные pilot secrets;
- проверит Compose-конфигурацию;
- соберёт Docker image или загрузит `okno-v-kitai-image.tar`, если IT положил offline image рядом с проектом;
- запустит web и scheduler;
- дождётся `healthy`;
- выполнит smoke checks;
- откроет `http://127.0.0.1:3000`;
- сохранит локальные данные доступа в `.pilot-access.txt`.

Для остановки используйте **STOP.bat**, для проверки — **STATUS.bat**.

## Linux / macOS

```bash
./start.sh
```

Остановка и статус:

```bash
./stop.sh
./status.sh
```

На macOS launcher может попытаться запустить Docker Desktop автоматически. На Linux Docker Engine должен быть установлен и daemon должен быть доступен текущему пользователю.

## Важная граница

One-click означает, что после однократной установки Docker ручная установка Node.js/npm и ручное редактирование `.env` для базового pilot-mode не нужны. Корпоративный SSO/TLS/DNS всё равно настраиваются IT отдельно, потому что они зависят от инфраструктуры компании.

При отсутствии доступа к npm registry IT может заранее предоставить `okno-v-kitai-image.tar`. В таком случае START использует `docker load`, проверяет tag `okno-v-kitai:1.6.1-pilot` и запускает сервис без пересборки.
