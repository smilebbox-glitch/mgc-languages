# Requirements & Verification Matrix — v4.4

## Цель

Собрать в одном доказательном digital thread путь от требования до результата проверки без дополнительных перегруженных экранов.

```text
Requirement
  ├─ Source document / clause
  ├─ System / Function
  ├─ Part / Special Characteristic
  ├─ Acceptance criteria
  ├─ Verification plan
  │    ├─ DV / PV / test
  │    ├─ Run@Rate
  │    ├─ inspection / measurement
  │    ├─ simulation / analysis
  │    └─ Design Review
  ├─ Evidence
  └─ ECR / ECO
```

## Правила доказательности

1. Статус `PASSED` не заменяет evidence.
2. Через API passed требует хотя бы одного доступного evidence-документа, passed Launch Trial или approved Design Review.
3. После изменения требования старый verification автоматически считается stale.
4. Source document и evidence подчиняются Document ACL; Project/Area access не расширяет эти права.
5. Critical/Safety/Regulatory requirement без verification создаёт critical blocker.
6. Failed verification создаёт critical blocker независимо от вручную выставленных readiness-статусов.

## Score

Матрица показывает пять объяснимых gate: Source, Traceability, Verification Plan, Verification Result, Change Closure. Score включается в Project Readiness только после появления первого требования, поэтому обновление старого проекта не меняет score задним числом.

## Не является compliance certification

Модуль хранит связи и evidence. Он не определяет автоматически юридическое, homologation, functional-safety или OEM compliance. Customer-specific requirements и корпоративные approval gates должны задаваться ответственными функциями.
