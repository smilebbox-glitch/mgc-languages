# Process Digital Thread — Pilot Acceptance

Проверку рекомендуется выполнять на одном ограниченном автомобильном процессе и только на тестовых/разрешённых данных.

## Сценарий 1 — Сборка

1. Создать Assembly line → Station 10 → Torque operation.
2. Связать рабочую инструкцию и part number.
3. Добавить torque parameter с target/lower/upper limits и unit Nm.
4. Связать Special Characteristic, PFMEA и Control Plan с `process_operation_id`.
5. Убедиться, что операция отображает PFMEA/Control Plan links и не создаёт gap при полном наборе evidence.

## Сценарий 2 — Сварка

1. Создать Body/Welding line и spot-welding operation.
2. Добавить fixture и gauge.
3. Установить истёкшую дату калибровки gauge.
4. Проверить, что Process Readiness показывает calibration blocker.

## Сценарий 3 — Дефект / 8D

1. Создать critical process defect на конкретной операции.
2. Без 8D убедиться в critical blocker.
3. Связать существующий 8D и повторно открыть process thread.
4. Убедиться, что gap «defect without 8D» исчез, а сам открытый critical defect остаётся видимым до закрытия процесса.

## Сценарий 4 — ACL между цехами

1. Project доступен группе `engineering-ai-users`.
2. Assembly area доступна этой группе.
3. Paint area доступна только отдельной `engineering-secret`.
4. Создать Paint document, APQP/PFMEA/Control Plan, milestone и Paint line.
5. Войти пользователем только `engineering-ai-users` и открыть «Все зоны».
6. Paint данные не должны появиться ни в documents, quality, process tree, milestones, readiness evidence или timeline.

## Сценарий 5 — Граница MES/SCADA

Проверить, что в UI/API Process Digital Thread отсутствуют действия Start/Stop/Write/Setpoint/PLC command. Система должна хранить инженерную структуру и evidence, но не управлять оборудованием.

## Exit criteria

- корректная line/station/operation hierarchy;
- стабильные Core Tools links по operation ID;
- area/document ACL leakage = 0;
- process readiness объясняет каждый gap;
- старые проекты без процесса не штрафуются;
- управление производственным оборудованием отсутствует.
