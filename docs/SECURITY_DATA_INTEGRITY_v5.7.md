# v5.7 Security & Data Integrity

## Defense in depth
1. FastAPI RBAC remains authoritative at route level.
2. PostgreSQL `FORCE ROW LEVEL SECURITY` protects user-owned learning tables.
3. Transaction-local context is bound as `app.user_id`, `app.role`, `app.department` after authentication.
4. User: own rows. Manager: own department. Admin/system maintenance: all rows.
5. SQLite development mode cannot enforce PostgreSQL RLS and is not an enterprise security equivalent.

## Audit integrity
Audit records are SHA-256 hash chained. PostgreSQL serializes chain append with an advisory transaction lock; retention advances a persisted anchor before deleting the expired prefix. `/api/admin/audit/verify-chain` detects modification/removal/reordering inside the retained chain. Central SIEM/WORM storage is still recommended for production-grade immutability.

## Acceptance
Run `tests/v57_security_data_integrity_test.py`. On a real PostgreSQL pilot, IT must additionally execute cross-department negative tests against the deployed DB role and verify RLS is FORCE-enabled.
