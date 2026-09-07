# Process Digital Thread — v4.2

## Назначение

Модуль связывает инженерную структуру производственного процесса с уже существующей цифровой нитью проекта. Он рассчитан на автомобильное производство и не заменяет MES/SCADA.

```text
Проект
  → Производственная зона
    → Линия
      → Станция
        → Операция
          → Оборудование / оснастка / измерительное средство
          → Параметр процесса
          → Special Characteristic
          → PFMEA
          → Control Plan
          → Дефект
          → 8D / ECR / ECO
```

## Производственные зоны

Операции наследуют зону от линии: R&D/Engineering, Stamping, Body/Welding, Paint, Assembly, Components, Logistics, Quality, Manufacturing Engineering или Testing/Validation. В режиме «Все зоны» сервер всё равно применяет ACL каждой зоны; этот режим не является повышением прав.

## Устойчивая связь с Core Tools

PFMEA и Control Plan могут содержать `process_operation_id`. Это предпочтительнее свободного текста `process_step`: перенос/переименование операции не ломает связь с Core Tools.

Процессная операция может иметь:
- part number;
- cycle time (справочно);
- рабочую инструкцию/evidence document;
- PFMEA и Control Plan;
- process parameters;
- оборудование/fixture/tool/gauge;
- defects/8D.

## Process Readiness

Если в проекте уже настроен Process Digital Thread, появляется дополнительный advisory gate «Процесс». Он анализирует, в частности:
- отсутствие рабочей инструкции;
- отсутствие PFMEA или Control Plan у операции;
- специальную характеристику без соответствующего control item;
- отсутствие reaction plan;
- незаданные target/limits у активного process parameter;
- просроченную калибровку измерительного средства;
- просроченное обслуживание оборудования;
- high/critical process defect;
- high/critical defect без связанного 8D.

Старые проекты без процессной структуры не получают штраф только из-за того, что модуль ещё не настроен.

## Automotive operation hints

UI предлагает только контекстные подсказки. Примеры:
- Body/Welding: spot welding, MIG/MAG, adhesive, hemming, geometry check;
- Paint: pretreatment, E-coat, sealer, primer, basecoat, clearcoat, oven;
- Assembly: torque, press fit, clipping, fluid fill, functional/EOL;
- Stamping: blanking, forming, trimming, piercing, inspection;
- Logistics: receiving, kitting, sequencing, packaging, material flow.

Это не обязательные технологические маршруты и не подменяет утверждённую технологическую документацию предприятия.

## Безопасность

Доступ вычисляется по цепочке:

```text
Engineer SSO
 → Project ACL
 → Manufacturing Area ACL
 → Document ACL
 → Process/Quality data
```

Проектная сводка не повышает доступ. Если пользователь не имеет прав на Paint, «Все зоны» не покажет Paint line/process/PFMEA/Control Plan/milestones или скрытые документы.

## Граница продукта

v4.2 не отправляет команды оборудованию, PLC, роботам, torque controllers, paint process equipment или конвейерам. Интеграция с реальными производственными системами в этой версии — только концептуально read-only evidence/source scope и требует отдельного security/OT review.
