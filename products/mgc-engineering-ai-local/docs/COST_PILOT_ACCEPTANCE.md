# v4.6 Cost & Engineering Economics — Pilot Acceptance

Пилот рекомендуется проводить на одном реальном автомобильном узле и 3–10 деталях.

## 1. Текущая и target baseline

1. Создать `current` baseline в RUB.
2. Создать `target` baseline.
3. Добавить одинаковый набор деталей.
4. Проверить вручную итоговую стоимость на автомобиль.
5. Проверить variance и annualized impact.

**PASS:** результат совпадает с ручным контрольным расчётом.

## 2. Material breakdown

Для одной детали задать массу, цену материала, scrap, conversion, logistics и packaging.

**PASS:** формула полностью объяснима, hidden assumptions отсутствуют.

## 3. Tooling

Задать tooling cost без amortization volume.

**PASS:** tooling не включён молча в unit cost и показано предупреждение.

Затем задать объём амортизации.

**PASS:** unit tooling = tooling cost / explicit volume.

## 4. Supplier quotation

Создать quotation с evidence. Проверить status и validity. Затем установить дату validity в прошлом.

**PASS:** selected expired quotation даёт advisory warning.

## 5. ECR/ECO cost impact

1. Создать ECR по тестовой детали.
2. Создать baseline `change`, связанный с ECR.
3. Указать reference baseline.
4. Изменить стоимость детали.

**PASS:** сервис показывает unit delta и annual delta, но не изменяет ECR/ECO approval автоматически.

## 6. Localization scenario

Создать baseline `localization` для альтернативного локального supplier.

**PASS:** сценарий можно сравнить с current, при этом Supplier Readiness остаётся отдельным показателем из v4.5.

## 7. ACL

Подготовить данные двух производственных зон, одна из которых закрыта для тестового инженера.

**PASS:** economics workspace не раскрывает cost lines/quotes скрытой зоны или детали.

## 8. Technical readiness isolation

Создать current cost выше target >10%.

**PASS:** economics показывает critical advisory gap, но технический Project Release Readiness score не меняется только из-за стоимости.

## 9. Evidence Pack

Сформировать Cost Evidence Pack.

**PASS:** snapshot содержит baseline, расчёт и governance flags, но не объявляет Finance approval.

## 10. Production build gate

```bash
docker compose build
make dockle
make acceptance
```

Все три шага должны завершиться в корпоративном build environment до production deployment.
