# Least-Privilege Service Accounts — v6.0.5

Use separate identities per trust boundary. Do not reuse a human administrator credential for services.

- `mgc_runtime`: PostgreSQL DML only, used by API/worker.
- `mgc_migrator`: one-shot DDL/migration role, not available to long-running containers.
- PLM/PDM connector: read-only engineering-document/BOM scope.
- ERP connector: read-only approved material/MBOM/cost scope required by the pilot.
- MES connector: read-only genealogy/build scope.
- QMS connector: read-only defect/quality scope.
- webhook clients: dedicated client certificate plus dedicated HMAC secret per source system.
- OIDC application: no directory-write scopes; request only identity/groups required for authorization.

All credentials should be delivered by the corporate secret-management mechanism and rotated independently. MGC must never write credentials into engineering evidence, audit details or exported support bundles.
