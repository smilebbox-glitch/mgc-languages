# MGC Engineering AI Local v6.3.25 — Release Notes

## Тема релиза

**External Trust Anchoring & Evidence Retention Governance**.

v6.3.25 усиливает созданный в v6.3.24 acceptance/provenance ledger внешними trust-контролями и governance хранения доказательств. Инженерская бизнес-модель и схема PostgreSQL не менялись.

## Основные изменения

- signing keys получают bounded validity window (по умолчанию 180 дней) и rotation warning;
- expired/revoked key не может регистрировать новое signed evidence;
- историческая подпись остаётся проверяемой, если ключ был действителен в момент регистрации;
- append-only retention policy с минимальными сроками хранения;
- автоматическое удаление evidence приложением запрещено;
- legal hold place/release как отдельные immutable events;
- registry checkpoint после полной crypto verification;
- generic external tip-hash anchoring adapter (`shell=False`, JSON argv contract);
- external receipt обязан точно подтвердить tip sequence/SHA-256;
- WORM/object-lock adapter для checkpoint objects;
- receipt не принимается, если retention короче запрошенного или object digest не совпадает;
- governance status `PASS / CONDITIONAL / FAIL`;
- offline auditor bundle с event/object chain, manifest, audit и governance report;
- offline bundle verifier с ZIP traversal/symlink/tamper protection;
- Engineering Admin operations summary дополнен privacy-safe anchor/WORM/key/retention posture;
- `production_authorized=false` сохраняется во всех автоматизированных trust-проверках.

## Совместимость

- Application: `6.3.25`;
- DB schema: `6.3.13`;
- новая DB migration: отсутствует;
- controlled rolling/blue-green window: `6.3.24 ↔ 6.3.25` при общей schema `6.3.13`;
- bounded-context business API: 247 routes;
- legacy API contracts: 181/181 preserved.

## Проверка

Полный backend regression: **590/590 PASS**, **98/98 test-файлов**, failures/errors/skips: `0/0/0`.

Новый v6.3.25 governance preflight: **32/32 PASS**. Новый специализированный test module: **15/15 PASS** (входит в общий regression).

## Ограничения

Packaging environment не подтверждает реальный corporate WORM/object-lock, RFC3161/notary, HSM/KMS custody, live 15/30/100 load или physical failover. Эти доказательства должны быть получены на target infrastructure. Поэтому supply-chain/production status остаётся `CONDITIONAL`, а Production GO не выставляется автоматически.
