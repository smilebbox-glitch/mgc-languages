# MGC Languages v5.7.6 — RLS & Audit Core

## Goal

Continue decomposing the legacy `app.py` while preserving PostgreSQL FORCE RLS behavior, the tamper-evident audit chain, existing routes, database schema and user-facing behavior.

## Extracted governance boundary

`mgc.governance_core` does not import `app.py`. The current ORM models and runtime configuration are injected by `mgc_core.governance_bridge`.

The extracted core owns production implementations for:

- PostgreSQL transaction-local RLS identity (`app.user_id`, `app.role`, `app.department`);
- system-admin RLS context;
- deterministic audit metadata serialization;
- SHA-256 audit event hashing;
- advisory-lock protected audit append behavior on PostgreSQL;
- verification of the audit hash chain including retention anchors.

## Runtime binding order

The ASGI runtime now binds in this explicit order:

1. dependency-light security primitives;
2. RLS/audit governance core;
3. model-aware auth/session core;
4. route contract validation.

The order is a security contract: `mgc.auth_core` captures the already-extracted `apply_rls_context` callable when its FastAPI dependencies are built.

## Compatibility

v5.7.6 preserves:

- existing FastAPI routes and OpenAPI/API paths;
- RLS identity values and PostgreSQL `set_config(..., true)` transaction scope;
- `AUDIT_CHAIN_LOCK_ID` advisory-lock behavior;
- audit hash canonicalization and SHA-256 algorithm;
- `AuditLog` / `AuditAnchor` schema;
- retention-anchor continuity after old audit prefix deletion;
- existing `/api/admin/audit/verify-chain` output;
- auth/session behavior from v5.7.5;
- UI, Putonghua content and all language data.

No Alembic migration is required.

## Regression gates

The new `v576` shard verifies:

- deterministic governance primitives without importing `app.py`;
- exact PostgreSQL RLS context SQL and values;
- ASGI binding order so auth uses extracted RLS;
- live audit generation from real register/admin actions;
- parity between extracted verifier and existing audit endpoint;
- retention-anchor continuity;
- identical tamper detection after deliberate audit-row modification.

Docker CI asserts governance binding before starting runtime smoke.
