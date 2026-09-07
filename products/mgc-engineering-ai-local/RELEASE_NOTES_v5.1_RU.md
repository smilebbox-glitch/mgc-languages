# MGC Engineering AI Local v5.1.0

## Engineering Change Intelligence

v5.1 переводит Engineering Digital Thread из режима «как всё связано» в режим «что затронет изменение и что нужно перепроверить». Все новые функции являются advisory-only и не утверждают ECR/ECO, PPAP, sourcing, SOP или product release.

### Change Impact Simulator
- What-if анализ изменения детали без записи в PLM/ERP/ECR/ECO.
- Поддержаны сценарии: revision, material, thickness, geometry, supplier, quantity и unit cost.
- Cross-domain impact: Product/BOM, Design, V&V, Manufacturing, Supplier/PPAP, Cost и Release.
- Explainable impact paths показывают детерминированную цепочку связи.
- При заданных ценах и annual volume рассчитывается unit/annual cost delta.

### Automatic Stale Evidence Detection
- Статусы: `CURRENT`, `REVIEW_REQUIRED`, `STALE`, `MISSING`, `UNKNOWN`.
- Проверяется наличие current-revision drawing/CAD.
- Requirement Verification использует существующие requirement/source snapshots и stale-логику.
- PPAP проверяется относительно текущей ревизии и доступного evidence.
- Открытые ECR/ECO создают downstream review action.
- Immutable Release Baseline не переписывается при drift: система предлагает создать новый baseline после закрытия изменения.

### Engineering Action Queue
- Единая очередь из stale evidence, trace gaps и High/Critical открытых изменений.
- Приоритеты: critical / high / medium.
- Работает в контексте проекта и выбранной производственной зоны.

### Variant Impact Matrix
- Part × Vehicle Variant matrix.
- `included`, `excluded`, `unknown` остаются явными состояниями.
- UNKNOWN никогда не интерпретируется как включённая применимость.

### Workshop / Manufacturing Area Impact
- Открытые изменения сопоставляются с настроенными Process Operations.
- Показывается влияние по сварке, окраске, сборке, компонентам, логистике и другим разрешённым зонам.
- В симуляторе выводятся конкретные line / station / operation.

### Traceability Coverage
- Отдельные показатели: drawing, CAD, requirements, process, supplier, approved PPAP и release baseline coverage.
- Показывается weakest coverage и список missing parts.
- Coverage не меняет технический Project/Release Readiness.

### Full Digital Thread Diff
Новые baselines используют `mgc-release-baseline-v2` и дополнительно фиксируют:
- manufacturing process operations;
- engineering cost lines;
- architecture nodes;
- interfaces.

Baseline comparison теперь сравнивает BOM/documents плюс V&V, supplier, PPAP, ECR/ECO, critical issues, process, cost, architecture/interfaces, configuration и advisory readiness delta. Старые v1 baselines остаются читаемыми.

### Ask Digital Thread
- Объединяет детерминированные факты Digital Thread с существующим локальным RAG по доступной документации.
- Ответ явно разделяет graph facts и document RAG.
- ACL применяется до построения thread и до retrieval.

## UI
- Нет нового глобального меню.
- Одна сворачиваемая карточка `Engineering Change Intelligence · v5.1` под Digital Thread Explorer.
- Симулятор и подробные матрицы скрыты до открытия карточки.

## Runtime
- Все deterministic функции v5.1 работают на CPU.
- LLM требуется только для синтеза RAG-части `Ask Digital Thread`; при отсутствии LLM остаются graph facts и retrieval evidence.
- Обычный `docker compose build` поддерживается.
