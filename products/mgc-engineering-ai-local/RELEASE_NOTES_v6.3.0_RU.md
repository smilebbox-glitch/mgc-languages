# MGC Engineering AI Local v6.3.0
## Manufacturing Work Instructions & Station Intelligence

v6.3.0 добавляет управляемый контур рабочих инструкций для производственных инженеров и перевод инженерных данных. Основной UX: **цех → линия → станция → операция → рабочая инструкция**.

## Главное

- перевод BOM по запросу инженера на RU/EN/ZH без изменения исходного BOM;
- Translation Memory с защищёнными part number, кодами, размерами, единицами и числами;
- отдельный раздел «Инструкции» для создания, редактирования и загрузки WI;
- импорт китайских/английских инструкций с сохранением оригинала и отдельной русской рабочей версией;
- human-reviewed перевод обязателен до утверждения иностранной WI;
- WI lifecycle: draft → in_review → approved → obsolete;
- шаги, safety/quality checkpoints, PPE, инструменты/оснастка, роль, навык, cycle time и evidence;
- станции: роль оператора, headcount, work content, takt time;
- layout цеха/линии с интерактивным размещением станций и показом покрытия WI;
- создание линий, станций и операций прямо из нового workspace;
- area-scoped RAG по инструкциям; optional station/operation narrowing;
- Core даёт deterministic evidence retrieval, AI profile может использовать локальный LLM;
- никакого управления PLC/robot/torque controller/оборудованием — это engineering information layer, не MES-control;
- 12 additive API; все 181 legacy v6.2.0 method/path сохранены.

## Schema

Application version: `6.3.0`. Schema marker: `6.3.0`.

Добавлены `work_instructions`, `engineering_translation_memory`, `manufacturing_layouts`, `station_layout_placements`; `process_stations` получает additive поля operator/headcount/work-content/takt.
