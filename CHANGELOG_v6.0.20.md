# MGC Languages v6.0.20 — Adaptive Arcade Missions

Дата: 08.09.2026

## Что добавлено

v6.0.20 развивает игровой слой v6.0.18–v6.0.19 без увеличения числа механик сверх 20. Цель релиза — сделать игровой раздел менее однообразным и добавить ежедневную прогрессию.

### Daily Missions

Каждый день пользователь получает три разные задачи:

1. **Цеховая миссия** — игра, связанная с отделом/производственным направлением пользователя.
2. **Новая механика** — приоритетно выбирается игровая механика, которую пользователь ещё не пробовал.
3. **Точка роста** — повтор механики с самым слабым предыдущим результатом.

Набор определяется детерминированно по дате, пользователю, языку и отделу. Данные разных пользователей и языков не смешиваются.

### Boss Shift

После выполнения 3/3 ежедневных миссий открывается финальный Boss Shift. Тип босса зависит от направления:

- Окраска → Paint Shop Boss / Defect Detective;
- Логистика → Material Flow Boss / Logistics Flow;
- Кузов и компоненты → Body Shop Boss / Car Part Hotspot;
- Сборка → Assembly Boss / Build the Car;
- Качество → Quality Gate Boss;
- R&D → Engineering Boss / Build the BOM;
- Закупки → Supplier Boss / Dialogue Duel;
- остальные направления → Shift Boss / Shift Incident.

### Цеховая привязка

Перед стартом цеховой миссии и Boss Shift frontend передаёт соответствующую тему в существующий game backend. Это позволяет использовать профильный словарь по окраске, логистике, кузову/компонентам, сборке, качеству, R&D и закупкам.

## Что не изменилось

- 20 игровых механик Automotive Arcade сохраняются;
- backend-ограничение 5 ответов на игровую сессию сохраняется;
- XP anti-farm сохраняется;
- Factory Journey v6.0.19 сохраняется;
- словарный паритет сохраняется: 2029 Chinese / 2029 English в runtime;
- OIDC/SSO, роли, PostgreSQL, Alembic, RLS и Docker/LAN deployment не менялись.

## Файлы релиза

- `static/frontend/arcade_missions_v620.js`
- `static/arcade_missions_v620.css`
- `tests/v620_arcade_missions_test.py`
- `static/index.html`
- `static/frontend/boot.js`
- `.github/workflows/ci.yml`
- `.github/workflows/ci-v617-company-pilot.yml`

## Проверки

Оба активных CI-контура запускают отдельный regression test v6.0.20 и `node --check` нового frontend-модуля.
