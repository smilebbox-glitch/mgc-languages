# Pilot Acceptance — Requirements & Verification Matrix v4.4

## Участники

Используйте минимум две инженерные группы/учётные записи и один тестовый проект. Желательно взять реальное, но некритичное требование OEM/внутренней спецификации.

## Сценарий 1 — requirement trace

1. Загрузить доступный source document.
2. Создать критическое requirement и связать с деталью.
3. Проверить: matrix показывает source/trace, но `verification_missing` остаётся blocker.

## Сценарий 2 — false PASS protection

1. Создать verification без evidence.
2. Попытаться установить `passed`.
3. Ожидается HTTP 400: passed требует evidence/Launch Trial/approved Design Review.

## Сценарий 3 — DV/PV reuse

1. Создать/использовать passed DV/PV Launch Trial.
2. Связать verification с этим trial.
3. Ожидается effective verification без повторного ввода факта испытания.

## Сценарий 4 — stale verification

1. Подтвердить requirement с evidence.
2. Изменить текст требования или источник.
3. Ожидается `verification_stale`; Project Workspace требует review.

## Сценарий 5 — ACL

1. Создать requirement в Paint с source document, закрытым от Assembly.
2. Войти пользователем Assembly и открыть `Все зоны`.
3. Requirement/verification/evidence Paint не должны появиться в matrix, timeline или readiness blockers.

## Сценарий 6 — safety boundary

Проверить, что UI/API явно указывают advisory/traceability nature и не предоставляют кнопку автоматического compliance/release approval.
