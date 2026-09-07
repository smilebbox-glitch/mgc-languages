# v5.1 Engineering Change Intelligence — Pilot Acceptance

## Functional
1. Открыть проект и карточку `Engineering Change Intelligence · v5.1`.
2. Проверить Action Queue и Traceability Coverage.
3. Выбрать деталь и смоделировать Rev A→B + material/thickness change.
4. Убедиться, что выводятся Design, Validation, Manufacturing и Release impacts.
5. Добавить supplier change и убедиться, что появляются PPAP/capacity actions.
6. Задать unit cost before/after + annual volume и проверить deterministic annual delta.
7. Проверить `Почему это затронуто?` — path должен состоять только из сохранённых связей.
8. Проверить Variant Impact Matrix: UNKNOWN не должен становиться included.
9. Создать два v5.1 release baselines и сравнить process/cost/architecture domains.
10. Выполнить Ask Digital Thread и проверить разделение deterministic facts и RAG sources.

## Security
1. Скрыть один evidence document у supplier/cost/change/validation object — объект должен исчезнуть из thread/intelligence output целиком.
2. Пользователь без доступа к source documents baseline получает 404/`Baseline not found`.
3. Попытка симуляции hidden/unknown part возвращает generic `Part not found`.
4. Aggregate All zones не должен включать данные запрещённой manufacturing area.

## Governance
- What-if simulation не создаёт и не изменяет ECR/ECO.
- Stale engine не удаляет historical evidence.
- Advisory readiness delta не выдаётся за formal release score.
- Никакие machine-control команды не выполняются.

## Build-host gate

```bash
docker compose build
make dockle
make acceptance
```
