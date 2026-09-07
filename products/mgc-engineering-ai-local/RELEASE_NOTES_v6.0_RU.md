# MGC Engineering AI Local v6.0.0
## Engineering Intelligence Operating System

v6.0 — архитектурный рубеж проекта. Все доменные контуры v5.0–v5.8 сохранены, а над ними добавлен единый операционный слой для ежедневной инженерной работы.

## Главное

### Role-based Decision Cockpit

Одна верхнеуровневая карточка в Project Workspace показывает состояние проекта в контексте выбранной рабочей роли:

- Engineering;
- Manufacturing Engineering;
- Quality;
- Supplier / Localization;
- Program / Launch;
- Field Reliability;
- Engineering Leadership;
- Engineering Admin.

Выбор роли **не является авторизацией**. Он меняет только порядок и фокус уже доступной информации. Project / Manufacturing Area / Document ACL остаются сильнее любой роли Cockpit.

### Unified Action Inbox

Inbox детерминированно агрегирует действия из существующих controlled records:

- Digital Thread gaps и stale/missing evidence;
- high/critical ECR/ECO;
- Program Control blockers и due-date exposure;
- residual risks, ineffective changes и expired deviations;
- Configuration / Manufacturing Handover blockers;
- Pilot/Safe Launch recurrence и exit-review candidates;
- series quality/capability signals;
- DFMEA/V&V field gaps и campaign-review candidates;
- активные cross-domain workflow cases.

Priority рассчитывается из severity и due-date urgency. Inbox не меняет исходные записи и не закрывает их автоматически.

### Decision Queue

Отдельно выделяются пункты, где требуется явное человеческое решение/ревью: release/handover, residual risk, Safe Launch exit, DFMEA/V&V field gaps, campaign assessment и workflow ready-for-close.

### Cross-domain Engineering Workflows

Добавлена одна новая persistent сущность — `EngineeringWorkflowCase`. Это orchestration/evidence record, а не второй task tracker.

Шаблоны v6.0:

```text
change_to_release
impact → technical review → V&V → configuration → human release review

defect_to_change
containment → root cause → 8D → ECR/ECO → effectiveness

field_to_change
field triage → exposure → DFMEA/V&V → engineering change → field effectiveness

launch_blocker
triage → owner action → evidence refresh → human gate review

supplier_issue
incoming quality → supplier 8D → PPAP → Run@Rate/capacity → human release review
```

Stage progression детерминирован и аудируется. После последнего шага workflow получает `ready_for_close`; финальное закрытие/отмена через API требует Engineering Admin.

### Ask Engineering OS

Добавлен deterministic CPU-only ответ по текущему Cockpit:

- что требует внимания;
- что требует решения;
- какие workflows активны;
- какой общий engineering command brief.

Функция не зависит от LLM и не генерирует approval.

## UX

Нового глобального пункта меню нет. Engineering OS находится в верхней части Project Workspace, а детальные v5.x модули остаются ниже для drill-down.

## Security / governance

- role is focus, not permission;
- workflow с mixed visible/hidden evidence скрывается целиком;
- trigger/source-linked workflow требует visible evidence;
- human-facing API остаются под `get_identity`;
- human release / gate / campaign / engineering decisions остаются обязательными;
- v6.0 не заменяет PLM/PDM, ERP, MES, QMS, DMS, Warranty или корпоративный Project Management;
- CPU-first и air-gapped deployment сохранены.

## API v6.0

```text
GET   /api/v1/projects/{project_code}/engineering-os
POST  /api/v1/projects/{project_code}/engineering-os/ask
POST  /api/v1/projects/{project_code}/engineering-os/workflows
PATCH /api/v1/projects/{project_code}/engineering-os/workflows/{workflow_id}
```

## Build-host gate

В packaging environment отсутствуют Docker CLI/daemon и Dockle, поэтому настоящий image build/layer scan здесь не заявляется как выполненный.

На approved corporate build host:

```bash
docker compose build
make dockle
make acceptance
```
