# MGC Languages v5.9.9 — Frontend Shell Boundary

## Цель

Подготовить большой historical `static/app.js` к поэтапному разделению без одномоментной переписи интерфейса.

## Новая структура

Порядок browser assets фиксирован:

1. `static/frontend/runtime.js` — module registry и diagnostics.
2. `static/app.js` — historical bundle, временно остаётся источником основной UI-логики.
3. `static/auth_department.js` — первый выделенный frontend module.
4. `static/frontend/boot.js` — compatibility adapter и fail-closed DOM/runtime contract.

`MGCFrontend` предоставляет `register`, `has`, `get`, `list`, diagnostics и readiness state.

`boot.js` регистрирует адаптер `legacy-app`, через который новые модули могут получать API/state/navigation capabilities без прямой зависимости от всего historical bundle.

## Fail-closed contract

Boot проверяет наличие ключевых frontend functions и DOM IDs. При drift интерфейс отмечается `data-mgc-frontend="failed"`, diagnostics сохраняет причину, а пользователю показывается понятное сообщение вместо частично сломанного экрана.

## Auth module

Department-aware auth теперь регистрируется как `auth-department` и предпочитает capabilities из `legacy-app`. Capture-phase submit contract и обязательный department для browser UI сохранены.

## Совместимость

- UI/UX не меняется;
- API/OpenAPI не меняются;
- `static/app.js` не переписан и не увеличен;
- auth/login/department behavior v5.9.7 сохраняется;
- XP/SRS/games/admin/content/Путунхуа не меняются.

## Следующие frontend slices

После этой границы безопасно выносить по одному:

- API client + service status;
- games/practice UI;
- learning/course UI;
- notifications;
- admin/terminology;
- final state/navigation core.

Каждый новый module должен регистрироваться через `MGCFrontend` и иметь отдельный contract test.
