# MGC Engineering AI Local v6.0.5 — Enterprise Security Deployment

v6.0.5 is a production-hardening release. It adds no automotive business domain. The goal is to make the existing Engineering Intelligence OS deployable behind corporate identity, PKI, network segmentation and software-supply-chain controls.

## Required topology

Use the enterprise overlay together with the normal air-gap/runtime, SSO and webhook overlays. The public browser path is TLS → enterprise-edge → oauth2-proxy → gateway → API/frontend. Machine webhooks use a separate mTLS listener → webhook-edge → HMAC-verified backend webhook.

The internal application/data network remains Docker `internal: true`. PostgreSQL, Redis, Qdrant, Neo4j, MinIO, model servers, API and worker must not be host-published.

## Database least privilege

Create two PostgreSQL identities externally under DBA control:

- `mgc_migrator`: DDL rights required only by the one-shot schema migration job;
- `mgc_runtime`: DML on MGC tables/sequences, no CREATE/ALTER/DROP role/database rights.

Set `MGC_MIGRATION_DATABASE_URL` only for the deployment process and `MGC_RUNTIME_DATABASE_URL` for API/worker. The enterprise overlay disables startup DDL in API/worker and waits for `schema-migrate` to complete successfully.

## TLS and mTLS

`MGC_TLS_CERT_DIR` must contain:

- `server.crt` — corporate PKI server certificate;
- `server.key` — matching private key, filesystem-restricted and never committed;
- `client-ca.crt` — CA bundle trusted for machine integration clients.

Browser/SSO traffic listens on 8443 inside the container and permits TLS 1.2/1.3 only. HSTS is enabled. Machine integration traffic listens separately and requires a valid client certificate (`ssl_verify_client on`). HMAC/webhook signature verification remains required behind mTLS; the two controls are complementary.

## OIDC policy

Production defaults are fail-closed:

- corporate OIDC is the expected human auth mode;
- `aud` is required;
- asymmetric signature algorithm allowlist only;
- HTTPS issuer/JWKS required unless an explicit non-production exception is configured;
- discovered JWKS host must match issuer host or an explicit allowlist;
- token clock skew is bounded;
- parser/JWKS errors are never reflected verbatim to users;
- trusted headers are disabled in production by default.

A reverse proxy using trusted headers requires explicit enablement and `X-MGC-Proxy-Secret`; forwarded user/group headers alone are insufficient.

## Supply chain

Run:

```bash
make supply-chain-preflight
```

This creates a declared-component CycloneDX-style SBOM, scans the source tree for committed secret candidates, checks dependency-lock readiness and verifies enterprise security controls. The packaging environment cannot create the frontend lockfile offline; enterprise CI must generate/review `package-lock.json` from the approved internal npm mirror and set `MGC_REQUIRE_LOCKFILES=true`. Python images must use an approved resolved wheelhouse/SBOM for the declared requirement ranges. On the approved build host set `MGC_REQUIRE_CVE_SCANNER=true`; then Trivy or Grype is mandatory and the gate fails closed if no approved scanner is installed.

The offline SBOM produced in packaging describes declared components. It is not a substitute for a resolved image/filesystem SBOM and CVE scan on the actual built images.

## Audit governance

Engineering Admin has read-only audit export and retention controls:

- `GET /api/v1/security/audit/export`
- `GET /api/v1/security/audit/retention`
- `POST /api/v1/security/audit/retention?confirm=PURGE_AUDIT`

Exports are NDJSON, redact sensitive detail keys, include a cumulative export hash chain and return the full payload SHA-256 in response headers. Retention cannot be configured below `AUDIT_MIN_RETENTION_DAYS`; destructive application requires explicit confirmation and writes a new governance audit event.

## Production approval gates

Before pilot/production approval execute on the actual build/runtime host:

1. `docker compose build`
2. `make supply-chain-preflight` with mandatory CVE scanner
3. `make dockle`
4. SAST/dependency scan under corporate tooling
5. TLS certificate-chain and mTLS client-certificate test
6. OIDC/AD login, group removal, token expiry and audience-negative tests
7. database least-privilege negative test (runtime role cannot CREATE/ALTER/DROP)
8. backup/restore drill
9. `make acceptance`
10. security review sign-off

No static preflight or AI-generated assessment replaces penetration testing or the corporate security approval process.
