# MGC Engineering AI Local v6.3.6
## Enterprise Identity & Policy Enforcement

v6.3.6 — технический governance/security-релиз поверх v6.3.5. Новых automotive business-domain модулей релиз не добавляет. Цель — связать approval/release с корпоративной идентичностью и assurance без изменения существующих Project / Manufacturing Area / Document ACL.

## Главное
- расширенный `Identity`: OIDC subject, issuer, groups, ACR, auth-time, client-id, service-account flag;
- sanitized identity snapshot в approval/release evidence; bearer token не сохраняется;
- scoped Identity Policy: action + project + manufacturing area + entity type;
- allow/deny groups, OIDC requirement, required ACR, max authentication age;
- production re-auth gate для privileged actions;
- service accounts fail-closed запрещены для human approval, policy admin, delegation admin и Final Release;
- controlled delegation / absence replacement только для approval decision;
- Engineering Admin authority нельзя получить через delegation;
- approval stage и identity policy оба должны разрешить delegation;
- approval record hash-chain теперь дополнительно содержит identity/assurance evidence;
- Release Package Final Release хранит identity evidence;
- новый canonical Release Manifest с SHA-256 и без production write-back;
- optional PostgreSQL RLS foundation только для identity-policy/delegation tables;
- `ElectronicSignaturePort` для будущего корпоративного PKI/e-sign adapter, bundled implementation disabled;
- primary UI остаётся простым: identity/governance controls находятся только в admin/system surface.

## Runtime defaults
- `IDENTITY_POLICY_ENFORCEMENT_ENABLED=true`;
- `PRIVILEGED_ACTIONS_REQUIRE_OIDC_IN_PROD=true`;
- `PRIVILEGED_REAUTH_MAX_AGE_SECONDS=900`;
- `GOVERNANCE_POSTGRES_RLS_ENABLED=false`;
- `ELECTRONIC_SIGNATURE_MODE=disabled`.

## API
Шесть bounded contexts содержат 215 routes. Все 181 legacy v6.2.0 method/path contracts сохранены. v6.3.6 добавляет 5 identity/delegation endpoints и один Release Manifest endpoint.

## Schema
Application `6.3.6`, schema `6.3.6`. Добавлены `engineering_identity_policies`, `engineering_identity_delegations` и identity-evidence columns в approval/release records. Миграция additive/idempotent.

## Security boundary
MGC approval evidence остаётся tamper-evident engineering evidence и не объявляется УКЭП/qualified electronic signature. Release Manifest не выполняет автоматических записей в PLM/PDM/MES/PLC/robot/torque-controller.
