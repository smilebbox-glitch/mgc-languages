# MGC Engineering AI Local v5.2.0

## Engineering Knowledge Memory

v5.2 добавляет корпоративную инженерную память поверх Engineering Digital Thread и Change Intelligence.

### Historical Engineering Cases
- Поиск аналогов по ECR/ECO, 8D, process defects, Design Review и validation issues.
- Показываются проблема, принятое решение, сохранённый outcome, проект, деталь и источник.
- Поиск поддерживает текущий проект и портфель всех уже доступных пользователю проектов.

### Explainable Similarity
- Детерминированный CPU-only similarity score.
- Учитываются совпадение инженерных терминов, детали, производственной зоны и подтверждённого результата.
- Для каждого результата выводится `why_similar`.
- Similarity не считается доказательством одинаковой root cause.

### Lessons Learned Governance
- Добавлена таблица `engineering_lessons`.
- Исторический кейс можно сохранить как `draft` Lessons Learned.
- Только Engineering Admin может перевести урок в `validated`.
- Validation требует явного outcome и effectiveness.
- `archived` сохраняет историю, но исключает урок из активного reuse.

### Recurrence Detection
- Открытые defects/8D/ECR/validation issues сравниваются с закрытыми и валидированными историческими кейсами.
- Повторяемость показывается как advisory signal, без автоматического определения root cause.

### Ask Engineering Memory
- Вопросы вида «сталкивались ли мы с этим раньше?» используют ранжированные historical cases.
- Работает без GPU/LLM; генеративная модель не нужна для deterministic core.

### Security
- Project / Manufacturing Area / Document ACL применяются до формирования memory set.
- Mixed visible/hidden evidence => whole-case fail-closed.
- Portfolio scope не расширяет права пользователя.

### UI
- Новый глобальный раздел не добавлен.
- Одна сворачиваемая карточка `Engineering Knowledge Memory · v5.2` под Change Intelligence.
- Детальные кейсы, recurrence и Lessons Learned скрыты до раскрытия карточки.
