# Engineering Digital Thread Explorer — v5.0

## Назначение

v5.0 объединяет уже существующие инженерные сущности MGC Engineering AI Local в один **детерминированный цифровой поток изделия**. Explorer не создаёт вторую PLM, не копирует мастер-данные в новую предметную модель и не использует LLM для догадок о связях.

Основная цепочка:

```text
Vehicle / Variant
       |
Architecture / Interface
       |
Part / Assembly --- BOM --- Child Part
       |
       +--- Drawing / CAD / Specification
       +--- Requirement --- V&V --- Evidence
       +--- Manufacturing Operation --- Work Instruction
       +--- Supplier / Localization
       +--- Engineering Cost
       +--- Validation Issue
       +--- ECR / ECO
       +--- Immutable Release Baseline
```

Каждая связь появляется только из уже сохранённого контролируемого факта: part number, BOM row, source/evidence document ID, requirement ID, process operation, supplier record, cost line, ECR/ECO, architecture endpoint, configuration applicability или release snapshot.

## Два режима

### 1. Project Thread

В Project Workspace компактная карточка **Engineering Digital Thread** показывает общую связанность доступного проектного контекста:

- количество узлов и связей;
- количество critical edges;
- trace gaps;
- распределение по инженерным доменам;
- advisory coverage %.

Coverage % — это показатель полноты связей между уже настроенными доменами. Он **не изменяет Project/Release Readiness** и не является разрешением на выпуск.

### 2. Part Impact Thread

После выбора детали Explorer строит локальное окружение на глубину 1–5 связей. Навигация для поиска пути двунаправленная, но исходное направление каждой инженерной связи сохраняется в API.

Примеры цепочек:

```text
PART-001 → REQ-014 → VV-008 → Test report
PART-001 → OP-120 → WI-ASM-120
Supplier A → PART-001 → ECR-031
PART-001 → Architecture node → Interface IF-07 → REQ-014
PART-001 → Variant MY27-EU
Release DF-2027-01 → drawing/CAD/BOM evidence → PART-001
```

Explorer возвращает короткие explainable routes к наиболее важным доменам, чтобы инженер мог быстро ответить «почему этот объект связан с деталью».

## Поддерживаемые типы узлов

| Тип | Источник |
|---|---|
| Part / Assembly | `Part` + доступная проектная документация |
| Document / CAD | `Document` |
| Requirement | `EngineeringRequirement` |
| V&V | `RequirementVerification` |
| Manufacturing operation | `ManufacturingLine` / `ProcessStation` / `ProcessOperation` |
| Supplier / localization | `LocalizationItem` |
| Engineering cost | `CostBaseline` / `CostLine` |
| ECR / ECO | `ChangeRequest` |
| Validation issue | `ValidationIssue` |
| Architecture | `ArchitectureNode` |
| Interface | `InterfaceDefinition` |
| Vehicle variant | `VehicleVariant` / `ConfigurationApplicability` |
| Release baseline | `ReleaseBaseline` |

## Trace gaps

Explorer отдельно показывает разрывы трассировки, например:

- BOM содержит child part, но нет доступной детальной карточки;
- у детали нет доступного чертежа или CAD;
- active requirement не имеет V&V;
- V&V помечен `passed`, но отсутствует доступный evidence;
- производственная операция не имеет доступной work instruction;
- supplier/localization record не имеет evidence.

Разрыв — это сигнал инженеру. Он не исправляется автоматически и не создаёт фиктивную связь.

## ACL / fail-closed

Digital Thread строится **после** существующего Project / Manufacturing Area / Document ACL контекста.

Правила:

1. скрытый документ не становится узлом;
2. сущность, для которой указан evidence-набор, исключается, если весь этот набор не доступен пользователю;
3. скрытая деталь не появляется через BOM или архитектурную связь;
4. release baseline показывается только если пользователь всё ещё видит каждый source document snapshot;
5. запрос фокуса по недоступной детали возвращает `404 Part not found`, а не подтверждает существование скрытого объекта;
6. режим `Все зоны` не расширяет права пользователя.

## API

```http
GET /api/v1/projects/{project_code}/digital-thread
```

Query parameters:

```text
manufacturing_area=<area code>   optional
focus_part=<part number>         optional
depth=1..5                       default 3
max_nodes=50..500                default 280
```

Пример:

```http
GET /api/v1/projects/MY27/digital-thread?manufacturing_area=assembly&focus_part=PART-001&depth=3
```

Ответ содержит:

```text
summary
part_coverage
gaps
routes
nodes
edges
legend
policy flags
```

## Производительность и CPU-first

Explorer не запускает LLM/VLM и не требует GPU. Он выполняет обычные SQL-запросы к локальной БД и строит ограниченный in-memory graph. Поэтому функция работает в CPU-only профиле и остаётся доступной даже если генеративная модель отключена.

`max_nodes` ограничивает размер общего project view. Для крупных проектов рекомендуется выбирать конкретную деталь и depth 2–3.

## Authority boundary

Всегда действуют ограничения:

```text
advisory_only = true
deterministic_relationships_only = true
human_release_approval_required = true
plm_pdm_remains_product_structure_authority = true
erp_remains_financial_transaction_authority = true
```

Explorer — слой инженерной навигации, impact analysis и evidence traceability. Он не утверждает ECR/ECO, PPAP, sourcing, инвестиции, SOP или product release и не отправляет команды в MES/SCADA/PLC.
