# MGC Engineering AI Local v6.1.0
## Corporate Deployment & Pilot Launch Kit

v6.1.0 — упаковочный и deployment-релиз после серии production-hardening v6.0.1–v6.0.9. Нового automotive business-domain в релизе нет.

## Главное

- deterministic reference sizing для controlled pilot на 15 и 30 инженеров;
- enterprise-reference profile для нагрузок свыше 30 пользователей, который всегда требует target-host benchmark;
- admin-only API для deployment plan, network ports, launch checklist и launch readiness;
- default-deny corporate firewall matrix;
- AD/OIDC checklist;
- PLM/PDM/ERP/MES/QMS connectivity checklist;
- 6-недельный rollout plan для пилота на 15–30 инженеров;
- corporate pilot launch runbook;
- machine-readable deployment profile и launch checklist;
- schema/runtime marker 6.1.0 для fail-closed mixed-release readiness.

## Reference sizing

Профили являются консервативной стартовой точкой, а не обещанием throughput:

- `pilot_15` — до 15 пользователей;
- `pilot_30` — 16–30 пользователей;
- `enterprise_reference` — более 30 пользователей, только benchmark-driven sizing.

`POST /api/v1/deployment/plan` всегда возвращает `certification_required=true` и `deployment_authorized=false`.

## Corporate launch gate

`POST /api/v1/deployment/readiness` оценивает готовность начать **controlled pilot**. Mandatory gates включают target-host performance, Docker runtime acceptance, CVE/dependency evidence, OIDC/TLS/mTLS negative tests, DB least privilege, backup→restore, network/DNS/NTP/storage, integration reconciliation, InfoSec/Data Owner approvals, support rota, monitoring и operations rehearsal.

Возможные статусы:

- `NOT_READY` — отсутствует хотя бы один mandatory gate;
- `CONDITIONAL_READY` — mandatory gates зелёные, но есть recommended rollout gaps;
- `READY_TO_LAUNCH_CONTROLLED_PILOT` — все mandatory и recommended launch gates подтверждены.

Ни один статус не является Production GO. `deployment_authorized=false` и `human_change_approval_required=true` — инварианты.

## Сеть

По умолчанию host ingress ограничивается:

- 443/TCP TLS — browser/SSO;
- 9443/TCP mTLS — optional machine webhook edge.

PostgreSQL/Qdrant/Redis/Neo4j/MinIO/model/API internal ports не должны публиковаться в пользовательские сети.

## Rollout

Рекомендуемый rollout:

1. Week 0 — target-host technical acceptance;
2. Week 1 — 3–5 champions;
3. Weeks 2–3 — 10–15 пользователей;
4. Weeks 4–5 — 15–30 пользователей;
5. Week 6 — UAT + UX closure + Operations acceptance + human Go-Live board.

## Verification

- backend regression: 316/316 PASS;
- dedicated v6.1.0: 8/8 PASS;
- human-facing authorization: 232/232 guarded, 4 explicit machine/health exceptions;
- Docker static security: 38/38 PASS;
- Compose/runtime security: 100/100 PASS;
- Enterprise Security: 23/23 PASS;
- Corporate Deployment preflight: 13/13 PASS;
- Observability: 16/16 PASS;
- Game Day: 15/15 PASS;
- UX acceptance: 9/9 PASS;
- secret scan: 0 findings;
- declared SBOM: 37 components.

Реальные Docker build/Dockle/Trivy/Grype/AD-PKI/runtime restore/load tests не выполнялись в packaging environment и должны быть выполнены на approved corporate host.
