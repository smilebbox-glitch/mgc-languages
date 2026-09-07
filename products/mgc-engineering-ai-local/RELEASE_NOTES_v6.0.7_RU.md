# MGC Engineering AI Local v6.0.7 — UX Simplification & Pilot Feedback Closure

## Цель релиза

v6.0.7 — седьмой шаг production-hardening после v6.0.6. Новых automotive-доменов не добавлено. Релиз уменьшает когнитивную нагрузку Project Workspace и замыкает агрегированный feedback пилота в формальный remediation/verification loop.

## Action-first Project Workspace

Engineering Intelligence OS автоматически загружается в проекте и показывает только три слоя первого экрана:

- до 5 приоритетных действий для выбранной роли;
- до 3 пунктов Decision Queue, где требуется человеческое решение;
- до 3 guided workflows.

Полный Cockpit и специализированные v5.x-модули не удалены: они доступны через progressive disclosure / единый collapsed evidence drill-down.

## Role guided workflows

Добавлены рабочие маршруты для Engineering, Manufacturing Engineering, Quality, Supplier/Localization, Program/Launch, Field Reliability и Engineering Leadership. Role остаётся только UX-фокусом и никогда не расширяет Project / Manufacturing Area / Document ACL.

## Pilot feedback closure

Добавлена агрегированная сущность `PilotUsabilityIssue` и admin API:

- `GET /api/v1/pilot/studies/{pilot_id}/usability-issues`;
- `POST /api/v1/pilot/studies/{pilot_id}/usability-issues`;
- `PATCH /api/v1/pilot/studies/{pilot_id}/usability-issues/{issue_id}`.

Lifecycle: `OPEN -> ACCEPTED -> FIXED -> VERIFIED/CLOSED`. VERIFIED/CLOSED требует remediation и verification evidence. Записи не предназначены для оценки сотрудников и не должны содержать user/email/IP/query/VIN/document-viewing identifiers.

## Pilot GO boundary

- открытая CRITICAL usability issue -> controlled pilot `NO_GO`;
- открытая HIGH issue -> максимум `CONDITIONAL_GO`;
- verified/closed issue перестаёт быть open gate;
- final go-live по-прежнему подтверждается человеком вне MGC.

## UX preflight

Добавлен `make ux-acceptance-preflight`: bounded information budget, progressive disclosure, role-not-auth boundary, critical/high UX pilot gates и наличие runbooks.

## Проверка

- backend regression: **290/290 PASS**;
- dedicated v6.0.7: **8/8 PASS**;
- UX acceptance preflight: **9/9 PASS**;
- human API authorization: **212/212 guarded**;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **98/98 PASS**;
- enterprise security: **22/22 PASS**;
- secret scan: **0 findings**;
- Compose YAML: **13/13 PASS**;
- TSX transpile syntax: **PASS**;
- Python compileall / shell syntax / CPU / build / DR / performance / pilot preflights: **PASS**;
- BUILD_MANIFEST: **455/455 PASS**; ZIP integrity: **PASS**; cache artifacts: **0**.

Реальный Docker image build, Dockle, Trivy/Grype, production npm ci, resolved backend wheelhouse, AD/OIDC/mTLS negative tests и реальный user pilot в этой packaging-среде не выполнялись.
