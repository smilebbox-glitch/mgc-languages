# Launch & Plant Readiness — v4.3

## Назначение

Модуль помогает автомобильной инженерной команде собрать в одном месте доказательства готовности проекта, производственной зоны или линии к SOP. Это **advisory engineering workspace**, а не автоматическое разрешение на запуск производства.

## Что оценивается

- оснастка и оборудование;
- поставщики и PPAP;
- производственная мощность / Run@Rate;
- pilot build, DV, PV;
- упаковка и логистика;
- персонал и обучение;
- Safe Launch;
- незакрытые high/critical 8D и ECR/ECO.

Система повторно использует данные из Process Digital Thread и Core Tools. Например, просроченная калибровка измерительного средства, отклонённый PPAP или открытый critical 8D автоматически отражаются в Launch Readiness — их не нужно вводить второй раз.

## Два типа записей

### Launch Check

Контрольный пункт с владельцем, сроком, зоной/линией/деталью, evidence и статусом:

`planned → in_progress → ready / blocked / failed / waived`

Категории: tooling, equipment, supplier, capacity, pilot_build, validation, packaging, logistics, staffing, training, safe_launch, other.

### Launch Trial

Фактический запуск/прогон:

- Run@Rate;
- Pilot Build;
- DV;
- PV;
- Safe Launch trial.

Для Run@Rate можно хранить target rate, actual rate, duration, produced quantity и good quantity. Если запись отмечена `passed`, но actual rate ниже target rate, сервис всё равно формирует критический blocker.

## Принцип готовности

Launch score собирается только из настроенных gates. Ненастроенный gate не считается автоматически «нулём». Это позволяет внедрять модуль постепенно.

Все итоговые поля содержат:

```json
{
  "advisory_only": true,
  "human_sop_approval_required": true,
  "not_mes_or_scada": true
}
```

## Безопасность

Доступ наследует существующую цепочку:

`Engineer SSO → Project ACL → Manufacturing Area ACL → Document ACL`.

Режим «Все зоны» показывает только разрешённые пользователю производственные зоны. Evidence document IDs фильтруются повторно перед выдачей API.

## Что модуль НЕ делает

- не запускает линию;
- не отправляет команды PLC/роботам/torque controllers;
- не изменяет process setpoints;
- не заменяет PPAP/APQP/Customer Specific Requirements;
- не утверждает SOP автоматически.

## UX

В основном меню новых пунктов нет. В Project Workspace появляется одна сворачиваемая карточка **«Готовность к SOP»**. В закрытом состоянии пользователь видит только общий статус, gate-проценты и первые блокеры. Детали и формы открываются по запросу.
