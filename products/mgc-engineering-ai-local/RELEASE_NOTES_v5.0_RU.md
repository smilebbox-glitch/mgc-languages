# MGC Engineering AI Local v5.0.0

## Крупный рубеж: Engineering Digital Thread Explorer

v5.0 превращает набор отдельных инженерных модулей в единый навигационный цифровой поток изделия без создания второй PLM и без LLM-догадок о связях.

### Что добавлено

- единый graph view: Part/BOM → документы/CAD → требования/V&V → производственный процесс → supplier/localization → engineering cost → ECR/ECO → quality issues → vehicle architecture/interfaces → vehicle variants → immutable release baseline;
- **Project Thread** для общей связанности проекта;
- **Part Impact Thread** с глубиной 1–5 для локального анализа влияния;
- explainable routes от детали к связанным инженерным объектам;
- trace-gap detector для отсутствующих drawing/CAD, V&V, evidence, work instruction и BOM documentation;
- advisory cross-domain coverage metric;
- один компактный Explorer внутри Project Workspace, без нового глобального раздела;
- CPU-first: Explorer не вызывает LLM/VLM и не требует GPU.

### Security / governance

- Project / Manufacturing Area / Document ACL применяются до построения thread;
- evidence-backed сущности fail closed при недоступном evidence;
- release baseline скрывается, если недоступен хотя бы один source document;
- недоступный focus part возвращает generic `Part not found`;
- Explorer не меняет технический Release Readiness;
- PLM/PDM остаётся authority для product structure, ERP — для финансовых/производственных транзакций;
- human release approval обязателен.

### API

```text
GET /api/v1/projects/{project_code}/digital-thread
```

Параметры: `manufacturing_area`, `focus_part`, `depth=1..5`, `max_nodes=50..500`.

### Совместимость

v5.0 не требует новой БД-схемы: Explorer использует существующие контролируемые сущности v4.x. Все прежние workflows сохраняются.
