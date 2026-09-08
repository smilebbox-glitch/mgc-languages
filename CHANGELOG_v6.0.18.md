# MGC Languages v6.0.18 — Vocabulary Parity & Automotive Arcade

Дата: 08.09.2026

## Цель релиза

Сделать пилот заметно насыщеннее в трёх востребованных автомобильных направлениях и убрать дисбаланс между китайским и английским курсами, одновременно превратив раздел игр в полноценную практическую Automotive Arcade.

## Контент

- базовый китайский корпус: 1735 терминов;
- базовый английский корпус: 256 терминов;
- добавлен параллельный английский слой: 1479 терминов;
- добавлено по 240 новых shop-specific терминов в каждый язык;
- из них в каждом языке:
  - Окраска: +80;
  - Логистика: +80;
  - Кузов и компоненты: +80;
- общий `experience.extra_terms` применяется одинаково к обоим языкам;
- runtime валидирует точное равенство количества Chinese / English terms и уникальность IDs.

## Игры

Добавлено 20 отдельных игровых механик:

1. Word Match
2. Listening Sprint
3. Precision Check
4. Phrase Builder
5. Car Part Hotspot
6. Build the Car
7. Factory Router
8. Tool Selector
9. Defect Detective
10. Safety Spot
11. Quality Gate
12. Logistics Flow
13. Kanban Challenge
14. Build the BOM
15. Spec or NOK?
16. 10-Second Recall
17. Memory Garage
18. Odd One Out
19. Dialogue Duel
20. Shift Incident

`Car Part Hotspot` использует интерактивную SVG-схему автомобиля с кликабельными зонами деталей. Другие механики используют процессы производства, дефекты, безопасность, логистику, BOM, допуски и реальные рабочие коммуникации.

Backend по-прежнему ограничивает одну игровую сессию пятью ответами (`MAX_GAME_ANSWERS = 5`).

## Runtime

Новые корпуса активируются через `mgc/content_v618.py` как для исторического `app.py`, так и для основного production entrypoint `asgi.py -> mgc_core.runtime`.

Это устраняет риск ситуации, когда JSON-файлы присутствуют в репозитории, но реальные API продолжают отдавать старый словарь.

## CI / Regression

Добавлен `tests/v618_content_games_regression_test.py`, который проверяет:

- manifest и размеры сгенерированных корпусов;
- 80/80/80 shop additions в обоих языках;
- фактическую runtime-активацию;
- Chinese / English parity;
- 20 уникальных game types;
- соответствие frontend и backend каталогов;
- наличие Car Part Hotspot;
- five-answer backend cap.

LAN Docker smoke дополнительно проверяет parity через production ASGI runtime.

## Совместимость

- схема PostgreSQL/Alembic не менялась;
- OIDC/SSO contract не менялся;
- RLS/governance contract не менялся;
- one-click Company Pilot path сохранён;
- UX hardening v6.0.17, Pinyin fallback и Natural/Neural TTS preference сохранены.
