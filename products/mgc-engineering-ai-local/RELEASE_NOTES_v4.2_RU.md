# MGC Engineering AI Local v4.2.0 — Release Notes

## Главное

v4.2 добавляет Process Digital Thread для автомобильного производства: производственная зона → линия → станция → операция → оборудование/оснастка → параметр → Special Characteristic → PFMEA → Control Plan → defect/8D.

## Пользовательский интерфейс

Новых глобальных разделов меню не добавлено. В Project Workspace появилась одна сворачиваемая карточка «Производственный процесс». По умолчанию инженер видит только короткую сводку и gaps; дерево и редактор раскрываются по запросу.

## Core Tools

PFMEA и Control Plan получили `process_operation_id`, поэтому связь с реальной операцией не зависит от совпадения текстового названия процесса.

## Readiness

При наличии настроенного процесса проект получает дополнительный advisory process gate. Среди проверок: work instruction, PFMEA/Control Plan coverage, reaction plan, process limits, calibration/maintenance и high/critical defects/8D.

## Automotive areas

Доступны operation hints для Body/Welding, Paint, Assembly, Stamping, Components, Logistics, Quality, Manufacturing Engineering, Testing и Product Engineering.

## Security

Усилен режим «Все зоны»: он агрегирует только производственные зоны, разрешённые caller area ACL. Project access не повышает Document/Area permissions.

## Граница продукта

Process Digital Thread не является MES/SCADA и не управляет оборудованием. Все readiness/gap outputs являются advisory и требуют инженерного решения.

## Verification

- Backend: **87/87 PASS**
- Engineer-only human API: **89/89 protected**
- Dockerfile static security: **32/32 PASS**
- Compose/runtime static security: **82/82 PASS**
- `docker compose build` preflight: **PASS**
- v4.1 → v4.2 migration: **PASS**
- All-zones area ACL regression: **PASS**

Реальный Docker image build и Dockle image-layer scan должны выполняться на корпоративном Docker build-host; packaging runtime Docker daemon не предоставляет.
