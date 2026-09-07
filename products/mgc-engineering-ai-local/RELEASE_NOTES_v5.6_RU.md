# MGC Engineering AI Local v5.6.0
## Vehicle Build & Launch Intelligence

### Основной рубеж
v5.6 связывает инженерную конфигурацию с конкретным Pilot Build / pre-series / Safe Launch автомобилем и замыкает обратную связь на следующую сборку.

### Добавлено
- VIN/build-level `VehicleBuild` с variant / plant / line / build type / release baseline context;
- фактическая genealogy: part / revision / supplier / lot / serial;
- проверка полноты genealogy относительно доступной 100% Vehicle Variant конфигурации;
- связь build с существующим Process Defect без дублирования QMS-записи;
- recurrence clustering по failure mode + part + supplier + variant;
- Safe Launch controls с population, defect count, clean-build streak и human-only exit;
- explainable `Build → Defect → 8D → ECO → later build` feedback loop;
- компактная карточка v5.6 в Project Workspace без нового глобального меню;
- CPU-only deterministic core для всех новых расчётов.

### Governance
- MES / ERP / QMS остаются authoritative systems;
- система не управляет линией, PLC, роботом, MES release или containment автоматически;
- Safe Launch exit не выполняется автоматически;
- исчезновение дефекта после изменения не считается доказанной причинностью (`causal_claim=false`);
- Project / Manufacturing Area / Document ACL остаётся fail-closed.

### Schema
Новые additive tables:
- `vehicle_builds`;
- `build_genealogy_items`;
- `build_defect_links`;
- `safe_launch_controls`.

Upgrade wrapper: `ensure_v56_schema()`.
