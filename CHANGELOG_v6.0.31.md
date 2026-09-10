# CHANGELOG — v6.0.31

## Pilot UI Simplification

v6.0.31 сокращает пользовательский слой MGC Language Lab до функций, которые нужны для текущего корпоративного пилота. Релиз не меняет словарный контент, database schema или основной API contract.

### Removed from the pilot UI

- Убран пункт **«Презентация»** и прекращена загрузка executive showcase runtime.
- Убрана загрузка пользовательских **3D / Digital Vehicle** поверхностей.
- Убран отдельный пункт **XP** и XP pill из topbar.
- Убран пользовательский пункт **«Помощник»**.
- В **Курсе 30 дней** полностью скрыт блок **«Активность / Соберите пару»**.
- В китайских **Сценариях** скрыта русская фонетическая запись; остаются иероглифы, pinyin и русский смысл.

### Games fix

Исправлен конфликт маршрутизации Games:

- основной pilot route больше не принудительно открывает `game-lab-v618`;
- `games` передаётся стабильному владельцу `practice-games`;
- добавлен единый interception path и retry UI при ошибке открытия;
- экспериментальный Game World остаётся вне основного пользовательского маршрута пилота.

### Word Match / in-game navigation hotfix

- В **Word Match** варианты ответа восстанавливаются из `item.options`, поэтому карточки выбора не должны отображаться пустыми.
- Выбранный вариант нормализуется в числовой индекс перед отправкой результата на `/api/games/{session_id}/finish`, чтобы backend scoring получал ожидаемый тип.
- Во время активной игры добавлена кнопка **«← К играм»**. Она сбрасывает текущую локальную игровую сессию и возвращает пользователя к каталогу игр без перезагрузки страницы.
- Регрессионный тест v6.0.31 проверяет наличие hotfix runtime, восстановление Word Match и возврат к каталогу игр.

### UI / visual refresh

- Добавлен слой `static/pilot_simplified_v631.css`.
- Упрощена topbar и sidebar navigation.
- Убрана лишняя поисковая строка из topbar для пилота.
- Уменьшены тени, декоративные поверхности и визуальная плотность.
- Прогресс на главной теперь не показывает XP-метрику.
- Профессиональные темы используют локальные SVG-изображения вместо абстрактных градиентов.
- Hero-иллюстрации китайского и английского треков заменены на новые локальные 2D SVG-иллюстрации автомобильного производства.
- Сохранена адаптация под ноутбуки и мобильные экраны.

### Verification

Для актуального v6.0.31 прошли основные release checks:

- Python compile и API architecture contract;
- Chinese/English content parity и backend game contract;
- v6.0.31 pilot regression;
- PWA privacy/offline security и release guard;
- syntax check активного JavaScript;
- полный LAN Docker Compose smoke test: PostgreSQL + application + Nginx, readiness через Nginx, проверка текущего HTTP surface и runtime contracts.

### Preserved contracts

- Chinese + English tracks.
- 2029 vocabulary terms per language.
- Pinyin for Chinese learning content.
- Existing server-side scoring and API paths.
- PostgreSQL / Nginx / Docker Compose / LAN deployment.
- PWA support.
- No database migration.

### Product decision

Тяжёлые визуальные и AI-функции не удаляются из истории разработки, но не являются частью текущего pilot UI. Их возврат следует рассматривать после реальной пользовательской обратной связи и подтверждения бизнес-пользы.
