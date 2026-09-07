# MGC Engineering AI Local v4.1.0 — Release Notes

## Automotive Quality & Industrialization

Добавлен единый quality-контур внутри Project Workspace:
- APQP deliverables;
- Special Characteristics;
- PFMEA;
- Control Plan с фазой Safe Launch;
- PPAP evidence/submission workflow;
- 8D problem solving;
- цифровые связи Special Characteristic → PFMEA → Control Plan;
- quality gaps и новый project quality gate;
- area-aware и document-ACL-aware фильтрация.

## Интерфейс

Основное меню не расширено. В проекте появилась одна карточка `Качество и индустриализация`, свёрнутая по умолчанию. Она показывает только score/gaps; подробные инструменты открываются по запросу пользователя.

## Governance

- Система не содержит закрытые формы, rating tables или Action Priority tables AIAG/VDA.
- PFMEA S/O/D и Action Priority вводятся/настраиваются организацией.
- Внутренний risk band используется только как advisory navigation signal.
- Любой readiness score остаётся рекомендательным; выпуск требует человека.

## Safety / access

Все новые quality API требуют engineer identity. Project/manufacturing-area access не расширяет Document ACL. Hidden evidence is not promoted into quality workspace responses.
