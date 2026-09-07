# MGC Engineering AI Local v5.3.0

## Closed-Loop Engineering Intelligence

v5.3 замыкает инженерный цикл: **решение → изменение → производство/качество → effectiveness → Engineering Memory**.

### Engineering Decision Record
- проблема, альтернативы, выбранный вариант и rationale;
- ожидаемый результат и принятый инженерный риск;
- связь с Part / ECR/ECO / evidence;
- controlled status для approval/verification;
- подтверждённый effectiveness попадает в историческую инженерную память.

### Production Feedback & Planned vs Actual
- наблюдаемый объём выпуска и число дефектов;
- defect rate до/после изменения;
- planned vs actual cost / mass / cycle-time deltas;
- evidence/provenance без попытки заменить MES/ERP/QMS.

### Change Effectiveness Monitoring
- observation → effective / ineffective / inconclusive;
- target, baseline, observed result, population и evidence;
- финальный effective/ineffective требует Engineering Admin;
- результат автоматически становится доступным Engineering Knowledge Memory как исторический evidence case.

### Deviation / Waiver Management
- released vs requested revision;
- причина, quantity limit, validity window, affected variants, risks, approvals;
- явный runtime-статус `expired` без переписывания исторической записи;
- approved/active/closed — human controlled.

### Engineering Risk Register
- Probability × Severity × Detectability (1–5);
- initial и residual deterministic score/band;
- mitigation/evidence links;
- accepted/closed требует Engineering Admin.

### Defect Root-Cause Explorer
- candidate paths через recent ECR/ECO, explicit 8D, repeated process defects и supplier incoming quality;
- explainable path для каждого кандидата;
- всегда `causal_claim=false`: система формирует направления расследования, а не объявляет root cause.

### Supplier Quality Closed Loop
- supplier/localization → PPAP → incoming quality → defect/8D;
- aggregate incoming defect rate и repeated failure modes;
- evidence fail-closed при недоступных источниках.

### Risk-Based Validation Planner
- deterministic scope от material / thickness / geometry / supplier / revision change;
- REQUIRED / REVIEW / candidate NOT IMPACTED;
- `human_vv_scope_approval_required=true`.

### Early Warning / Release Confidence / Engineering Pulse
- defect-rate increase after change;
- ineffective change review;
- high/critical residual risk;
- expired deviations;
- repeated supplier 8D;
- planned-vs-actual miss;
- отдельные Product / V&V / Supplier / Quality / Risk / Configuration confidence domains вместо непрозрачного одного процента.

## UI
- одна сворачиваемая карточка `Closed-Loop Engineering Intelligence · v5.3` внутри Project Workspace;
- нового глобального пункта меню нет;
- контекст Manufacturing Area сохраняется;
- интерфейс показывает детали только после явного открытия соответствующего блока.

## Governance
- PLM/PDM остаётся authoritative product-structure system;
- ERP остаётся authoritative financial/transaction system;
- QMS остаётся authoritative quality-disposition system;
- MES/SCADA остаётся authoritative production/machine layer;
- v5.3 не отправляет PLC/robot/machine commands;
- AI/детерминированные алгоритмы не утверждают release, waiver, risk acceptance или root cause.

## Compatibility
- CPU-first deterministic core retained;
- GPU/LLM не требуется для основных v5.3 функций;
- v5.3 additive/idempotent schema wrapper;
- v5.0–v5.2 функции и старые release baselines сохраняются.
