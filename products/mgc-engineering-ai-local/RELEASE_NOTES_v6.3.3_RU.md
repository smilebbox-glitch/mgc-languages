# MGC Engineering AI Local v6.3.3
## Database & Domain Integrity Hardening

v6.3.3 — технический релиз поверх v6.3.2. Новых бизнес-разделов не добавляет. Цель — защитить совместную инженерную работу от lost update, несогласованного audit и некорректных значений на уровне БД.

## Главное

- optimistic `row_version` для Change Request, Process Station, Work Instruction и Manufacturing Layout;
- API поддерживает `expected_version` / `expected_layout_version` без breaking change для старых клиентов;
- stale edit возвращает HTTP 409 `EDIT_CONFLICT` и не перезаписывает более новую версию;
- UI Work Instructions передаёт version token для редактирования, статуса, перевода и review;
- layout placement использует version token всего layout и повышает его после каждой расстановки станции;
- критичные WI/station/layout изменения и audit event коммитятся одной Unit of Work;
- ECR/ECO state transition и hash-chained ChangeEvent теперь атомарны;
- DB-level invariants: BOM quantity > 0, station headcount >= 1, non-negative takt/cycle values;
- migration v6.3.3 проверяет legacy data и fail-closed останавливается при нарушениях вместо автоматической правки;
- PostgreSQL получает additive CHECK constraints; SQLite pilot — guard triggers для legacy schema;
- API route compatibility сохранена: 181/181 legacy v6.2.0 routes и все v6.3.0 manufacturing routes остаются на месте.

## Версии

- Application: `6.3.3`
- Schema: `6.3.3`

Требуется additive migration с v6.3.2 до v6.3.3.

## Verification

- full backend inventory: 362/362 PASS (76 test files, sharded execution);
- Domain Integrity preflight: 25/25 PASS;
- Architecture: 27/27 PASS;
- Dependency Profiles: 18/18 PASS;
- Bounded Contexts: 21/21 PASS;
- API compatibility: 5/5 PASS;
- Ports & Adapters: 25/25 PASS;
- Projection Reliability: 26/26 PASS;
- Docker static security: 38/38 PASS;
- Compose/runtime security: 100/100 PASS;
- Enterprise Security: 23/23 PASS;
- Corporate Deployment: 13/13 PASS;
- Observability: 16/16 PASS;
- Game Day: 15/15 PASS;
- UX: 9/9 PASS;
- API authorization: 253 guarded human-facing routes; 4 explicit exceptions;
- secret scan: 0 committed candidates;
- build preflight: PASS.

Real target-host gates remain mandatory: PostgreSQL migration rehearsal/backup, Docker BuildKit image build, resolved dependency locks, CVE/image scan, OIDC/PKI negative tests and controlled UAT.
