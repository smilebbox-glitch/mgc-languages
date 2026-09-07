# MGC Engineering AI Local v4.6.0 — Release Notes

## Cost & Engineering Economics

Добавлен отдельный advisory-слой инженерной экономики для автопрома:

- current / target / change / localization / scenario baselines;
- deterministic part cost breakdown;
- material mass/price/scrap;
- conversion/logistics/packaging/overhead;
- explicit tooling amortization;
- supplier quotations;
- target-cost variance и annual impact;
- ECR/ECO cost delta;
- Cost Evidence Pack;
- cost summary в карточке детали.

## UX

Основное меню не расширено. В Project Workspace появилась одна сворачиваемая карточка **«Стоимость и экономика»**. По умолчанию показываются только 4 показателя и максимум 3 advisory gaps.

## Governance

Cost layer не входит в технический Release Readiness. ERP/Finance остаются финансовым system of record. Сервис не принимает sourcing/investment/release решения автоматически.

## Verification

См. `VERIFICATION.md` и `docs/COST_PILOT_ACCEPTANCE.md`.
