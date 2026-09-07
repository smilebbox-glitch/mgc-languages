# MGC Engineering AI Local v3.9.0 — Engineering Project Workspace

## Что добавлено

- Новый простой раздел **«Проекты»**.
- Проект объединяет корневую сборку, детали, BOM, CAD/чертежи, замечания, Design Review, ECR/ECO и milestones.
- Детерминированный показатель готовности по пяти gate: документация, качество, изменения, Design Review, этапы.
- Каждый блокер показан отдельно; скрытая логика «AI решил, что готово» не используется.
- Показатель готовности только рекомендательный; выпуск требует человеческого согласования.
- BOM assembly tree строится только по видимой подтверждённой структуре.
- Project ACL не повышает права на исходные документы; Document ACL остаётся сильнее.
- Добавлены проектные milestones и аудит их изменения.
- Additive/idempotent upgrade v3.8 → v3.9.
- Сохранены CPU/GPU runtime, one-command Docker build, Engineer-Only Access, КОМПАС/T-FLEX, Drawing↔3D, Design Review и ECR/ECO.

## Проверка при упаковке

- Backend tests: 67/67 PASS.
- Human API authorization: 65/65 guarded; 2 explicit machine/health exceptions.
- Dockerfile static security: 32/32 PASS.
- Compose/runtime security: 82/82 PASS.
- `docker compose build` structural preflight: PASS.
- TSX transpile syntax check: PASS.

Реальный Docker image build и Dockle layer scan должны выполняться на корпоративном Docker build-host.
