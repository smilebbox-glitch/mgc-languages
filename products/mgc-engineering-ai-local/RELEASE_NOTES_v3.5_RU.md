# MGC Engineering AI Local v3.5.0 — Release Notes

## Главное

v3.5 превращает платформу в закрытый инженерный сервис: production-доступ только через корпоративный SSO и инженерные группы. Также добавлены история работы по каждому чертежу и однокнопочный Design Review Agent.

## Engineer-Only Access

- production `AUTH_MODE=oidc`;
- edge gate через oauth2-proxy по инженерным группам;
- повторная group-проверка внутри FastAPI;
- `gateway/api/model-server` не публикуются на host в production;
- shared API-key human access блокируется в production;
- обычный инженер не видит раздел «Для IT»;
- отдельная группа `engineering-ai-admins` для инженерных администраторов;
- pilot API-key topology оставлена только как явный non-production override.

## Drawing Activity Timeline

- новый `DocumentActivity`;
- автоматическая запись открытия, загрузки, AI-вопросов, CAD/drawing analysis, Linking, VLM inspection, similarity, CAD conversion и Design Review;
- ручные инженерные заметки «что сделано / проверено / решено»;
- append-only API;
- SHA-256 chain + отдельный head/count anchor и автоматическая проверка целостности, включая удаление последней записи.

## Design Review Agent

Одна кнопка **«Полная проверка конструкции»** собирает:

- 3D/CAD;
- drawing;
- BOM;
- текущую/предыдущую ревизию;
- Drawing ↔ 3D coverage;
- validation issues;
- VLM disagreements;
- material/thickness consistency.

Результат показывает risk score, чек-лист, findings и следующие действия без необходимости читать технический JSON.

## Совместимость

Добавлена идемпотентная additive migration v3.4 → v3.5 для `DesignReview.report_json`. Новая таблица истории создаётся через SQLAlchemy без удаления старых данных.

## Проверка релиза

Финальные числа проверки фиксируются в `VERIFICATION.md` и `security-reports/STATIC_SECURITY_VERIFICATION.txt` после упаковки.
