# Engineering Change Intelligence — v5.1

## Назначение

v5.1 строит explainable impact analysis поверх v5.0 Engineering Digital Thread. Сервис не создаёт новый system of record и не изменяет инженерные объекты во время what-if симуляции.

```text
Proposed change
   |
   v
Visible Part / Digital Thread
   +--> Product / BOM / Variants
   +--> CAD / Drawing / Architecture
   +--> Requirements / Verification / Issues
   +--> Process / Work Instruction / Workshop
   +--> Supplier / PPAP
   +--> Engineering Cost
   +--> ECR/ECO / Release Baseline
   |
   v
Impact categories + stale evidence + actions + explainable paths
```

## Freshness states

- `CURRENT` — evidence подтверждено как актуальное по доступным данным;
- `REVIEW_REQUIRED` — автоматическая инвалидизация некорректна, требуется инженерная проверка;
- `STALE` — детерминированный snapshot/источник устарел;
- `MISSING` — необходимое evidence отсутствует;
- `UNKNOWN` — недостаточно данных для вывода.

Исторические документы и immutable baselines не удаляются и не переписываются.

## What-if simulator

Поддерживаемые признаки изменения: revision, material, thickness, supplier, unit cost, quantity и explicit geometry change. Результат `simulation_only=true` и `does_not_modify_engineering_records=true`.

## Full Digital Thread Diff

Release baseline schema v2 расширяет snapshot process/cost/architecture/interface данными. Сравнение v1↔v2 допускается; отсутствующий в старом snapshot домен трактуется как исторически незафиксированный, а не как доказанное отсутствие в реальном изделии.

## Security

Каждый evidence-bearing объект включается только если все его referenced documents доступны пользователю. Mixed visible/hidden evidence fail-closed. Неизвестный focus part возвращает generic `Part not found`.

## Authority boundaries

- PLM/PDM — product structure authority;
- ERP/Finance — financial transaction authority;
- MES/SCADA/PLC — production control authority;
- formal ECR/ECO, PPAP, sourcing, SOP and release approval остаются человеческими/корпоративными процессами.
