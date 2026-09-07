# MGC Engineering AI Local v3.5.0 — заметки к релизу

## Главное

- КОМПАС-3D: M3D/A3D/T3D/CDW/FRW/SPW/KDW.
- T-FLEX CAD: GRB.
- Нативный файл сохраняется без изменений; анализ выполняется по контролируемой STEP/PDF/DXF-производной.
- Для пользователя — одна кнопка **Подготовить для анализа**; выбор CAD gateway и типа производной выполняется автоматически.
- Поддержка Drawing ↔ 3D из v3.3 сохранена.

## Безопасность

- MGC Docker images: non-root, HEALTHCHECK, без `ADD`, без секретов в Dockerfile ENV, удаление setuid/setgid.
- Compose: read-only rootfs, `no-new-privileges`, `cap_drop: ALL`, tmpfs.
- Внутренние сервисы air-gap topology не публикуются напрямую на host.
- Air-gap bundle блокирует `latest`/неподтверждённые image placeholders.
- Native CAD gateway требует API key по умолчанию и должен работать за TLS/mTLS в корпоративной сети.

## Проверено в среде сборки исходников

- backend: 47/47 tests passed;
- Dockerfile static Dockle/CIS preflight: 32/32 PASS;
- Compose/network security preflight: 41/41 PASS;
- Compose YAML + shell syntax + Python compile: PASS;
- frontend TSX syntax/transpile: PASS.

## Что должен выполнить IT на Docker build host

```bash
cp .env.airgap.example .env
# заполнить секреты и approved pinned image references
make build
make dockle
make bundle
```

Реальный Dockle image scan не был выполнен в среде упаковки исходников, поскольку в ней отсутствуют Docker daemon/CLI и Dockle. Это зафиксировано в `VERIFICATION.md` и security report.
