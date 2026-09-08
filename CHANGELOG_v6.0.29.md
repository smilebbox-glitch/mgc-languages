# v6.0.29 — Release Candidate / Pilot Freeze

## Цель релиза

v6.0.29 — это **RC1 для Company Pilot**. Новая пользовательская функция не добавляется. Релиз фиксирует уже проверенный функциональный состав после v6.0.28 и переводит проект в режим pilot freeze.

## Что зафиксировано

- 2029 китайских терминов и 2029 английских терминов;
- точный Chinese / English parity;
- 20 Automotive Arcade game types;
- максимум 5 backend-ответов на игровую сессию;
- существующий anti-farm;
- текущий список обязательных frontend-модулей;
- Factory Journey, Daily Missions, Arcade Mastery;
- Production Game Depth, Decision Chains и Dynamic Factory;
- Shift Simulation и Personal Shift Analytics;
- Manager / Team Analytics и Top-10;
- Adaptive Training v6.0.27;
- UX / Accessibility / Performance hardening v6.0.28;
- PostgreSQL + Nginx + Docker Compose LAN/Company Pilot deployment contract.

## Release manifest

`RELEASE_MANIFEST_v6.0.29.json` является машинно-проверяемой спецификацией RC1. Он содержит:

- game contract;
- frontend module contract;
- product layers;
- deployment contract;
- critical files;
- freeze rules.

## Release Candidate Guard

`scripts/release_candidate_guard.py` сверяет manifest с runtime и репозиторием:

1. проверяет 20 game types и их точный список;
2. проверяет `MAX_GAME_ANSWERS == 5`;
3. проверяет 2029/2029 runtime vocabulary parity;
4. сравнивает точный `requiredModules` из `boot.js` с frozen manifest;
5. проверяет `pilotCandidate: v6.0.29`;
6. проверяет обязательные deployment/critical files;
7. запрещает неявное расширение функционального scope после RC;
8. подтверждает, что v6.0.29 не добавляет новый runtime JS/CSS слой.

## Operability hardening

После RC freeze добавлен отдельный `tests/v629_operability_smoke_test.py`. Это не новая пользовательская функция, а release/test hardening.

Дополнительно исправлена рассинхронизация runtime metadata: `mgc.config.APP_VERSION` теперь по умолчанию равен `6.0.29`, поэтому `/api/meta` больше не должен отдавать старый номер `6.0.20`.

Main LAN CI теперь через реальный Nginx проверяет:

- `/health/live`;
- `/health/ready`;
- `/api/meta` и точную версию `6.0.29`;
- загрузку основной HTML-оболочки;
- загрузку критических frontend assets;
- `pilotCandidate: v6.0.29` в `boot.js`;
- отказ в доступе к персональному adaptive-training API и manager analytics API без авторизации;
- PostgreSQL, modular runtime и frozen release guard внутри контейнера.

## Freeze policy

После RC1 без явного снятия freeze разрешены только:

- blocker bug fixes;
- security fixes;
- deployment fixes;
- исправления документации;
- test/release-gate fixes.

Новые game types, frontend feature modules, database migrations, XP paths и продуктовые функции в v6.0.29 не допускаются.

## Совместимость

v6.0.29 сохраняет все пользовательские и backend-контракты v6.0.28. Исторический regression v6.0.28 переведён в forward-compatible режим, а точный активный номер пилота теперь принадлежит v6.0.29 release gate.
