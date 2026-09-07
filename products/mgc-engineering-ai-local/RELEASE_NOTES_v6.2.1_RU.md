# MGC Engineering AI Local v6.2.1
## Bounded-Context Router Decomposition

v6.2.1 — patch-релиз архитектурного упрощения поверх v6.2.0. Новых бизнес-domain функций не добавляет и не требует миграции БД. Цель — физически отразить шесть bounded contexts в HTTP source tree, убрать 3k-line route monolith и сохранить существующий `/api/v1` контракт.

## Главное

- бывший `backend/app/api/routes.py` на 3218 строк физически разрезан на шесть route-модулей;
- 181 legacy handler распределён по bounded contexts без изменения method/path/handler body;
- `routes.py` уменьшен до 19-строчного compatibility facade;
- общие ACL/visibility helpers вынесены в route-free `context_shared.py`;
- добавлен `context_registry.py` для profile-aware runtime composition;
- Core не монтирует Supplier & Field, если соответствующие capabilities отсутствуют;
- Core сохраняет Intelligence & Search через deterministic `lexical_search`, даже без Qdrant/model-server;
- runtime contract теперь публикует `active_bounded_contexts` и отдельный `schema_version`;
- APP version: `6.2.1`; DB schema marker остаётся `6.2.0`;
- добавлен machine-readable baseline `docs/API_CONTRACT_v6.2.0.json`;
- API contract preflight доказывает сохранение всех 181 method/path и AST handler implementation;
- API access/security scanners обновлены для recursive route-tree scanning.

## Physical route ownership

| Bounded context | Legacy handlers |
|---|---:|
| Engineering Core | 53 |
| Configuration & Change | 39 |
| Manufacturing & Quality | 39 |
| Supplier & Field | 22 |
| Intelligence & Search | 20 |
| Platform & Operations | 8 |
| **Total** | **181** |

Подробная ownership map: `docs/API_BOUNDED_CONTEXTS_v6.2.1.md`.

## Compatibility

Внешний `/api/v1` contract сохранён. v6.2.1 не меняет database schema и не вводит новую migration. Existing clients/integrations не должны менять URL из-за данного refactor.

Profile composition не является authorization. Project / Manufacturing Area / Document ACL, Identity dependencies, capability gate и human approval boundaries остаются обязательными.

## Verification highlights

- context-router decomposition: 21/21 PASS;
- legacy API contract equivalence: 4/4 PASS;
- v6.2 architecture preflight: 27/27 PASS;
- affected architecture tests: 15/15 PASS;
- API authorization preflight: 236 human-facing routes guarded; 4 explicit non-human/public exceptions;
- Enterprise Security: 23/23 PASS;
- Docker static security: 38/38 PASS;
- Compose/runtime security: 100/100 PASS;
- Corporate Deployment: 13/13 PASS;
- UX: 9/9 PASS;
- Observability/Reliability: 16/16 PASS;
- Game Day: 15/15 PASS;
- build preflight: PASS;
- deterministic secret scan: 0 findings.

## Required corporate build-host gates

Как и v6.2.0, релиз не считается Production GO без реального `docker compose build`, resolved dependency lock/wheelhouse, CVE/image scan, target-host runtime/performance tests, SSO/PKI negative tests, backup→restore rehearsal, integration reconciliation, UAT и Operations acceptance.
