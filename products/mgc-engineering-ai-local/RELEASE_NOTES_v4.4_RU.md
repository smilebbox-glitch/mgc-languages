# MGC Engineering AI Local v4.4.0 — Release Notes

## Основное изменение

v4.4 добавляет автомобильную **Матрицу требований и подтверждения (Requirements & Verification Matrix)** поверх Project Workspace.

Цепочка: `требование → источник → система/функция → деталь → Special Characteristic → verification → evidence → ECR/ECO`.

### Требования

Поддерживаются категории OEM, regulatory/legal, customer, system/interface, manufacturing, quality и internal. Для требования можно задать критичность, источник/ссылку на пункт, систему/функцию, детали, критерий приёмки и предполагаемый verification method.

### Verification

Поддерживаются analysis, inspection, test, review, demonstration, simulation и measurement; фазы Prototype/DV/PV/Pre-launch/Production. Существующий LaunchTrial (Run@Rate, DV, PV) и approved Design Review могут использоваться как evidence без дублирования данных.

`PASSED` не считается доказательством сам по себе. API разрешает passed только при наличии доступного evidence-документа, passed Launch Trial или approved Design Review.

### Защита от устаревшего evidence

При подтверждении фиксируются timestamp версии требования и SHA-256 исходного документа. Если требование позже изменено, старое подтверждение получает `stale` и требует повторного review.

### Интерфейс

Новый пункт основного меню не добавлен. В Project Workspace есть одна сворачиваемая карточка **«Требования и подтверждение»**, которая по умолчанию показывает только score, четыре показателя и максимум три ближайших gap.

### Граница продукта

Матрица является системой трассировки/evidence. Она не является автоматическим сертификатом соответствия OEM, законодательству, homologation, ISO 26262 или другим стандартам. Финальная оценка соответствия остаётся в утверждённом корпоративном процессе.
