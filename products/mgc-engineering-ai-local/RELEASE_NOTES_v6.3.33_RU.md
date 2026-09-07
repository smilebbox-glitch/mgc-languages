# MGC Engineering AI Local v6.3.33 — Release Notes

## Тема релиза

**Pilot Readiness & UX Simplification**.

v6.3.33 не добавляет новый доменный модуль. Релиз упрощает ежедневную работу инженера перед реальным пилотом и сохраняет все технические safety-контуры v6.3.32.

## Основные изменения

- основная навигация сокращена до 5 рабочих зон: Главная, Проекты, Детали/BOM, Инструкции, Поиск/ИИ;
- Object 360, документы, проверки и ECR/ECO сохранены как контекстные drill-down поверхности;
- добавлен evidence-backed **Action Center** на главной и внутри проекта;
- Action Center вычисляется из текущего project readiness evidence, не создаёт новый source of truth и ограничен 12 действиями;
- critical действия сортируются первыми; каждое действие содержит ссылку на исходный engineering object;
- добавлен **Project Focus Workspace** с прямыми переходами к деталям/BOM, документам, WI, изменениям и AI-поиску;
- тяжёлые engineering panels переведены под progressive disclosure «Полная инженерная картина»;
- IT/Admin поверхность остаётся отделена от инженерного интерфейса;
- DB schema остаётся 6.3.13, миграции нет;
- API route count остаётся 247, legacy API 181/181 сохранён;
- adjacent rolling/blue-green window: **6.3.32 ↔ 6.3.33**;
- resilience certification v6.3.32 остаётся обязательным baseline/release gate.

## Governance

- Action Center advisory-only;
- human decision required;
- никакого автоматического release approval;
- source-system authority не меняется;
- ACL не расширяется;
- AI/UX слой не оценивает производительность сотрудника.

## Проверки

- backend regression: **676/676 PASS**, **106/106 test files**;
- full `mgcctl verify --scope full`: **26/26 PASS**;
- Pilot Readiness preflight: **16/16 PASS**;
- focused version/release-safety regression: **67/67 PASS**;
- Python compileall: PASS;
- shell syntax: **29/29 PASS**;
- Compose YAML parse: **19/19 PASS**;
- API contract: **181/181 legacy preserved**, **247 current routes**.

Supply-chain и финальная package-integrity фиксируются в `VERIFICATION_v6.3.33.md`.

## Supply-chain status

- 159/159 provenance entries validated;
- 152/159 source-package inputs present;
- 7 corporate lock/wheelhouse artifacts intentionally absent;
- immutable corporate image refs 0/14 in this packaging environment;
- SBOM 37 components;
- status `CONDITIONAL`, `production_authorized=false`.


## Package / environment boundary

- controlled payload before embedded manifest: **1079 files**;
- cache artifacts: **0**;
- symlinks: **0**;
- Docker CLI в packaging environment отсутствует, поэтому image build/live runtime не заявляются как выполненные;
- ZIP members: **1080** вместе с embedded `BUILD_MANIFEST.json`;
- duplicate/missing/extra/size/SHA mismatch: **0**;
- embedded manifest: **PASS**;
- ZIP CRC/test: **PASS**.
