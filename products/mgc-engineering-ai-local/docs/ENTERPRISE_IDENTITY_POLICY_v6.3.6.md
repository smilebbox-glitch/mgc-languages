# Enterprise Identity & Policy Enforcement — v6.3.6

## Purpose
v6.3.6 binds the v6.3.5 approval/release governance layer to corporate identity assurance without changing Project / Manufacturing Area / Document ACL semantics.

## Identity evidence
For OIDC users MGC retains only a sanitized approval evidence snapshot: user, subject (`sub`), issuer, groups, `acr`, `auth_time`, issued/expiry time, client id and service-account flag. Bearer tokens, signatures, JWKS payloads and raw claims are not stored in approval records.

## Policy Enforcement Point
Controlled actions are evaluated against an optional scoped identity policy:

`action + project + manufacturing area + entity type`.

Specific policies override broader policies. Deny groups win over allow groups. A policy may require corporate OIDC, accepted `acr` values, a maximum authentication age, explicitly allowed groups and whether delegation is permitted.

Controlled actions include approval submit/decision, approval-policy administration, identity-policy administration, delegation administration, Release Package create/submit and Final Release.

## Human-only actions
Service accounts cannot perform approval decisions, policy/delegation administration or Final Release even if an upstream identity provider accidentally maps a privileged group to the machine principal. Service-account status comes from a configurable OIDC actor-type claim; MGC never guesses it from a username prefix.

## Re-authentication
In production, privileged actions can require OIDC and a bounded authentication age. The default maximum is 900 seconds. Corporate deployments may additionally require one or more approved `acr` values.

## Delegation / absence replacement
Delegation is deliberately narrow. v6.3.6 only permits `approval_decision` delegation. It requires an explicit validity window, project/area/entity scope, reason and delegated groups. Engineering Admin group membership is always removed from delegated authority. A stage must also declare `delegation_allowed=true`, and the resolved identity policy must allow delegation.

## Approval evidence
Approval cases store submitter identity evidence. Approval records store approver identity plus assurance/policy/delegation evidence alongside the existing hash-chain. This does not constitute a qualified electronic signature.

## Release Manifest
`GET /api/v1/projects/{project_code}/release-packages/{package_id}/manifest` returns a canonical handover manifest containing package/item hashes, approval chain head, release identity evidence and a manifest SHA-256. It performs no PLM/MES write-back.

## PostgreSQL RLS boundary
`GOVERNANCE_POSTGRES_RLS_ENABLED=false` by default. When explicitly enabled on PostgreSQL, v6.3.6 installs RLS policy foundations only for `engineering_identity_policies` and `engineering_identity_delegations`. The wider Project/Area/Document ACL model remains application-enforced until a dedicated corporate DB-role/RLS certification is completed.

## Electronic signature boundary
`ElectronicSignaturePort` exists as an integration boundary. The bundled adapter is disabled and reports no qualified signature capability. A future corporate PKI/e-sign adapter can sign the already computed manifest digest without changing the engineering approval domain model.
