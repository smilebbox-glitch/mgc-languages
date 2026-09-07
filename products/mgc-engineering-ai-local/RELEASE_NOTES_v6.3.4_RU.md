# MGC Engineering AI Local v6.3.4
## Engineering Revision & Conflict Management

v6.3.4 — технический multi-user hardening поверх v6.3.3. Релиз не добавляет новый automotive domain: он делает Work Instructions, Manufacturing Layouts и Engineering Change безопаснее для параллельной работы нескольких инженеров.

## Главное

- structured HTTP `409 EDIT_CONFLICT` возвращает `expected_version`, `current_version` и текущий authoritative record;
- UI показывает «актуальная версия ↔ мои несохранённые изменения» и не выполняет auto-merge;
- controlled revision creation для Work Instructions и Manufacturing Layouts;
- новая ревизия всегда стартует как `draft`, сохраняет lineage и не изменяет исходную Approved/Obsolete ревизию;
- foreign-language WI не наследует reviewed-перевод: translation state новой ревизии становится `stale` до повторного перевода и human review;
- revision snapshots с canonical JSON + SHA-256 для forensic comparison;
- idempotency receipts для критичных retry-prone WI/layout write flows;
- повтор того же `Idempotency-Key` с другим payload блокируется;
- duplicate Change Approval stage блокируется DB uniqueness; migration fail-closed при legacy duplicates;
- Engineering Admin получает Integrity dashboard и историю edit conflicts;
- WI/layout/change diff остаётся advisory-only: safety, quality, tooling и технологические шаги не сливаются автоматически.

## Новые API v6.3.4

```text
GET  /api/v1/changes/{change_id}/diff
POST /api/v1/projects/{project_code}/work-instructions/{instruction_id}/revisions
GET  /api/v1/projects/{project_code}/work-instructions/{instruction_id}/diff
POST /api/v1/projects/{project_code}/layouts/{layout_id}/revisions
GET  /api/v1/projects/{project_code}/layouts/{layout_id}/diff
GET  /api/v1/operations/integrity
GET  /api/v1/operations/conflicts
```

Operations endpoints являются Engineering Admin-only.

## Схема

- Application: `6.3.4`
- Database schema: `6.3.4`
- additive tables: `engineering_revision_snapshots`, `write_idempotency_records`, `edit_conflict_events`;
- unique approval-stage invariant для `change_approvals`;
- migration не auto-correct'ит неоднозначные legacy approval records.

## Совместимость

Все **181/181** method/path legacy-контракта v6.2.0 сохранены. Шесть bounded contexts содержат **198** routes; profile composition и ACL semantics сохраняются.

## Verification summary

- backend regression: **369/369 PASS** across 77 test files;
- Revision & Conflict preflight: **28/28 PASS**;
- Architecture: **27/27 PASS**;
- Domain Integrity: **25/25 PASS**;
- Projection Reliability: **26/26 PASS**;
- Ports & Adapters: **25/25 PASS**;
- Dependency Profiles: **18/18 PASS**;
- Bounded Context ownership: **21/21 PASS**;
- API contract: **5/5 PASS**;
- Docker static security: **38/38 PASS**;
- Compose/runtime security: **100/100 PASS**;
- Enterprise Security: **23/23 PASS**;
- API authorization: **260 guarded human-facing routes**, 4 documented exceptions;
- UX: **9/9 PASS**;
- Observability: **16/16 PASS**;
- Corporate Deployment: **13/13 PASS**;
- Game Day: **15/15 PASS**;
- deterministic source secret scan: **0 findings**;
- Python compileall / shell syntax / Compose YAML / build preflight: PASS.

## Build-host gates

`frontend/package-lock.json` всё ещё отсутствует, а backend requirements содержат declared version ranges. Поэтому dependency-lock status остаётся WARN. На approved corporate build host обязательны resolved npm lock/wheelhouse, CVE/SCA/image scan, real `docker compose build`, PostgreSQL migration rehearsal/backup→restore, OIDC/PKI negative tests и UAT.
