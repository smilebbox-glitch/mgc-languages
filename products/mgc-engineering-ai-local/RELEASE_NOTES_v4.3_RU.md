# MGC Engineering AI Local v4.3.0 — Release Notes

## Launch & Plant Readiness

v4.3 добавляет автомобильный слой готовности к SOP поверх Project Workspace, Process Digital Thread и Quality Core Tools.

### Основные функции

- единая компактная карточка «Готовность к SOP»;
- Launch Checks по tooling/equipment/supplier/capacity/logistics/training/Safe Launch;
- Launch Trials: Run@Rate, Pilot Build, DV, PV, Safe Launch;
- target vs actual capacity validation;
- автоматическое повторное использование PPAP, 8D, ECR/ECO и process asset readiness;
- readiness по производственным зонам с сохранением area/document ACL;
- новый project gate `launch`, включаемый только после настройки launch-данных;
- advisory-only status: финальный SOP approval остаётся за ответственным человеком.

### UX

Новый пункт главного меню не добавлен. Launch Readiness находится внутри Project Workspace и разворачивается только по кнопке.

### Security

- 94/94 human-facing API routes требуют engineer identity;
- 2 явных исключения: `/health` и HMAC webhook;
- Dockerfile preflight: 32/32 PASS;
- Compose/runtime preflight: 82/82 PASS.

### Migration

Новые таблицы `launch_readiness_items` и `launch_trials` создаются additive через SQLAlchemy `create_all`; `ensure_v43_schema()` сохраняет идемпотентную цепочку миграций v4.2.
