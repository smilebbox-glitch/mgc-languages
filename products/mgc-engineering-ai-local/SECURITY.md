# Security baseline — Local v6.0.9

## v6.0.8 UX privacy boundary

Usability feedback is stored as aggregate workflow/interface evidence. The UX issue API rejects the same participant/content identifier classes prohibited from pilot telemetry, and the system does not produce employee productivity scores. Role-specific landing pages are presentation-only and cannot expand Project, Manufacturing Area or Document ACL.

## v6.0.6 pilot privacy boundary

Pilot telemetry is aggregate-only and rejects user/email/IP/query/VIN/document identifiers. Pilot APIs inherit normal engineer identity enforcement; controlled GO remains human-only.

## v6.0.5 enterprise hardening

The enterprise profile adds a TLS 1.2/1.3 edge for human SSO traffic, a distinct mTLS-required machine webhook edge, strict production OIDC policy, explicit CORS allowlists, one-shot schema migration with separate database identity, admin-only redacted/hash-chained audit export and supply-chain gates for SBOM, secret scanning and external CVE scanning. Trusted identity headers are disabled in production by default.

The packaging environment does not claim completed penetration testing, zero CVEs or formal compliance certification. Production approval requires corporate PKI/IdP tests, resolved dependency/image SBOM, an approved CVE scanner, Dockle/container scan and independent security review.

## AI data boundary

In the default air-gapped deployment, company prompts, retrieved evidence, drawings and engineering metadata are sent only to the internal model service. Public AI APIs are not required. `AIR_GAPPED_MODE=true` rejects public inference endpoints unless they are explicitly allowed by corporate configuration, while firewall/VLAN policy remains the authoritative network control.


## Engineer-only authorization

Production human access is OIDC/SSO only. `oauth2-proxy` rejects users outside the configured engineering groups and the FastAPI backend independently validates the signed access token and repeats the group check. Shared API-key human access is disabled in production. The base gateway, API and model server do not expose host ports, preventing a normal network client from bypassing the SSO entry point.

A source preflight scans human-facing `/api/v1` routes and fails if a route is added without `Depends(get_identity)`. Health and the HMAC-signed machine webhook are explicit exceptions.

## Drawing audit integrity

Document activity is append-only through the application API and uses a SHA-256 previous-event chain plus a separate per-document head/count anchor. This detects ordinary row edits/deletions when history is read. It is tamper-evident rather than tamper-proof against a fully privileged database/application administrator; regulated deployments should export audit evidence to corporate immutable/WORM logging or SIEM.

## Native CAD boundary

КОМПАС-3D and T-FLEX native files are immutable source evidence. The Linux MGC core does not reverse-engineer the proprietary formats. Conversion is delegated to a licensed internal Windows gateway using the official vendor automation/API layer. The derivative receives its own SHA-256 and provenance relationship.

The reference gateway is secure-by-default:

- API key required unless explicitly disabled for a lab;
- extension/target allowlists and size/time limits;
- per-job temporary directory;
- `shell=False` process invocation;
- gateway API key removed from converter child environment;
- vendor stdout/stderr not returned through the API;
- TLS/mTLS and network allowlisting required for production.

## Container isolation

MGC-owned runtime images use non-root users and HEALTHCHECK. Compose hardening for API/worker/frontend/gateway/webhook edge applies `no-new-privileges`, drops Linux capabilities, uses read-only root filesystems and tmpfs for required writable paths. MGC-owned runtime Dockerfiles remove setuid/setgid permissions where possible and use `COPY` rather than `ADD`.

Database, vector store, object store, model-server, API, worker and frontend are not directly host-published in the air-gap topology; traffic enters through the hardened reverse proxy.

## Image supply chain

Air-gap Compose uses `pull_policy: never`. The air-gap bundle path rejects `:latest` and unresolved approved-image placeholders before image export. Model weights are staged separately with exact repository revision information and SHA-256 hashes. The bundle records the actual Docker image IDs transferred to the isolated environment.

Use the corporate container vulnerability scanner in addition to Dockle. Dockle checks image/configuration best practices and CIS-style checkpoints; it is not a replacement for CVE/SCA scanning.

## Verification evidence

See:

- `docs/DOCKLE_SECURITY.md`;
- `security-reports/STATIC_SECURITY_VERIFICATION.txt`;
- `VERIFICATION.md`.

The packaging environment passed **32/32 Dockerfile static checks** and **63/63 Compose/access/network checks** and **49/49 human-facing API authorization checks**. A real Dockle image scan must be executed on the Docker build host after the images are built; it is not claimed as completed in this source-packaging runtime.
