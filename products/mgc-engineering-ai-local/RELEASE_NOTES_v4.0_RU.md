# MGC Engineering AI Local v4.0.0 — Automotive Manufacturing Workspace

## Главное

- Добавлен единый производственный контекст для автопрома без разрастания меню.
- Зоны: R&D, Штамповка, Кузов/Сварка, Окраска, Сборка, Компоненты, Логистика, Качество, Технология производства, Испытания/Валидация.
- Project Workspace, документы, детали, проверки, ECR/ECO и AI/RAG могут работать в выбранной зоне.
- Документ при загрузке получает текущую зону; существующий документ можно переклассифицировать из карточки.
- Добавлен `ProjectArea` с owner/status/ACL.
- Milestones могут быть общими или zone-specific.
- RAG payload/index получает `manufacturing_area` и поддерживает строгий area filter.
- Для каждой зоны добавлен короткий automotive focus checklist.

## UX

- Sidebar не разрастается.
- Один компактный selector **«Зона»** в header.
- Один горизонтальный selector внутри проекта.
- IT/ACL configuration скрыта от обычного инженера.

## Security

- Engineer-only gate сохранён.
- 68/68 human-facing API routes требуют engineering identity.
- 2 explicit exceptions: `/health` и HMAC machine webhook.
- Project/Area membership не повышает Document ACL.

## Compatibility

- Additive/idempotent upgrade v3.9 → v4.0.
- Новая таблица `project_areas` создаётся стандартным `Base.metadata.create_all` до additive migration.
- В `documents` и `project_milestones` добавляется `manufacturing_area`.
- Legacy-документы остаются unclassified/common до явной классификации.
