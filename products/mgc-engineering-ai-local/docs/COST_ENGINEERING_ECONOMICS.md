# Cost & Engineering Economics — v4.6

## Назначение

Модуль предназначен для инженерной оценки стоимости автомобильной детали/узла и влияния технических решений на стоимость. Он не является бухгалтерской системой, ERP или автоматическим инструментом согласования sourcing/investment business case.

Основная цепочка:

```text
Part / BOM
   ↓
Mass + Material + Scrap
   ↓
Conversion / Logistics / Packaging
   ↓
Tooling + explicit amortization volume
   ↓
Supplier quotation
   ↓
Current / Target / Localization scenario
   ↓
ECR/ECO cost impact
```

## Cost Baseline

Поддерживаемые типы:

- `current` — текущая инженерная оценка;
- `target` — целевой cost scenario;
- `change` — сценарий после конкретного ECR/ECO;
- `localization` — сценарий локализации;
- `scenario` — прочий инженерный сценарий.

Baseline хранит валюту, годовой объём, при необходимости target cost на автомобиль/узел, reference baseline и связанный ECR/ECO.

## Cost Line

Строка связана с деталью и baseline. Есть два режима.

### Engineering breakdown

Детерминированно учитываются только явно заданные компоненты:

```text
Material = mass_kg × material_price_per_kg × (1 + scrap_rate_pct/100)
Unit cost = Material
          + conversion
          + logistics
          + packaging
          + overhead
          + other
          + tooling amortization
```

Tooling включается в unit cost **только если явно указан `tooling_amortization_volume`**. Иначе tooling показывается отдельно, чтобы система не придумывала срок/объём амортизации.

### Supplier quote

В режиме `quote` базой служит `supplier_unit_price`. Material/conversion не добавляются повторно, чтобы избежать double counting. Дополнительно могут быть явно заданы logistics, packaging, other и tooling amortization.

## Supplier quotation

Quotation хранит:

- supplier code/name;
- part/revision;
- currency;
- unit price;
- tooling cost;
- annual volume;
- validity date;
- status;
- evidence documents.

Выбранная просроченная quotation отображается как advisory gap. Selected quotation без доступного evidence также помечается.

## Target vs Current

Workspace рассчитывает:

- current cost / vehicle;
- target cost / vehicle;
- абсолютное и процентное отклонение;
- annualized variance при заданном годовом объёме;
- mass / vehicle;
- tooling total.

Экономические отклонения **не изменяют технический Release Readiness**. Это отдельный advisory слой.

## ECR/ECO impact

Baseline типа `change` требует ссылку на ECR/ECO и может ссылаться на reference baseline.

Сервис считает:

```text
Unit delta / vehicle = Change scenario − Reference scenario
Annual delta = Unit delta × Annual volume
```

Это позволяет увидеть инженерный cost impact изменения материала, толщины, конструкции, supplier switch или локализации.

## Evidence Pack

Cost Evidence Pack фиксирует snapshot baseline, строк, текущего/target cost, annual impact, ECR/ECO impacts и advisory gaps на конкретный момент.

## Governance

Всегда действуют флаги:

```text
advisory_only = true
finance_approval_required = true
erp_is_financial_system_of_record = true
no_automatic_sourcing_or_investment_approval = true
```

Модуль не должен автоматически:

- номинировать поставщика;
- утверждать инвестиции/tooling;
- изменять ERP-price;
- выпускать ECR/ECO;
- разрешать SOP/серийный выпуск.
