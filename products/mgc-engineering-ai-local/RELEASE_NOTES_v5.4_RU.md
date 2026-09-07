# MGC Engineering AI Local v5.4.0

## Engineering Program Control / Launch Command Center

v5.4 превращает существующий Digital Thread в объяснимый engineering-program control layer. Система связывает milestones с V&V, PPAP, launch readiness, ECR/ECO, Engineering Risk, production-quality feedback и release evidence, чтобы показать, что реально угрожает следующему Design Freeze / Release / SOP gate.

### Новое

- controlled `ProgramDependency` между engineering milestones;
- cycle prevention при создании dependency;
- explicit `lag_days` и `criticality`;
- next controlled gate detection: Design Freeze / Release / SOP;
- deterministic schedule propagation и forecast slip;
- explainable critical dependency chain по due-date/dependency slack;
- program maturity по Product / Program / V&V / Manufacturing & Launch / Supplier & PPAP / ECR-ECO / Quality / Risk;
- manufacturing-area maturity для доступных зон;
- blocker forecast из реальных engineering evidence/gaps;
- Engineering Command Brief и top-action queue;
- read-only what-if milestone slip simulation;
- одна компактная карточка v5.4 в Project Workspace, без нового глобального меню.

### Важная граница

Critical dependency chain не называется формальным CPM без authoritative activity durations/resources. Gate forecast — deterministic advisory indicator, а не ML-прогноз даты SOP и не автоматический gate approval.

### ACL

Project / Manufacturing Area / Document ACL сохраняет fail-closed поведение. Cross-domain source с недоступным evidence не попадает в Program Control aggregation.

### Runtime

Program Control не требует LLM/VLM и работает в CPU profile.
