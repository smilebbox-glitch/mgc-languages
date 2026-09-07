# v6.0.5 Threat Model

## Assets
Engineering CAD/drawings, EBOM/MBOM, requirements, supplier/cost data, VIN genealogy, quality/field data, identity/group claims, audit history, local model/evidence stores and integration credentials.

## Trust boundaries
1. Corporate browser/user ↔ TLS/SSO edge.
2. Machine integration client ↔ mTLS webhook edge.
3. Edge ↔ internal application network.
4. API/worker ↔ PostgreSQL/Redis/Qdrant/object store/model servers.
5. MGC ↔ PLM/PDM/ERP/MES/QMS connectors.
6. Build pipeline ↔ approved package/image registries.

## Priority threats and controls

| Threat | Primary controls | Residual requirement |
|---|---|---|
| Stolen/forged user token | OIDC issuer/audience/signature/claim validation, asymmetric alg allowlist, engineer groups | Corporate IdP MFA/session policy |
| Spoofed forwarded identity | trusted headers off in prod; optional proxy secret | Keep API unexposed and proxy secret protected |
| Network interception | TLS 1.2/1.3 edge; mTLS machine channel | Corporate PKI lifecycle/revocation |
| Compromised app container | non-root, cap-drop, no-new-privileges, read-only FS, internal network, runtime DB role | Host/container runtime patching |
| Supply-chain compromise | SBOM, secret scan, approved CVE scanner hooks, pinned image policy | Resolved SBOM, signatures/provenance in corporate CI |
| Malicious integration payload | versioned contracts, quarantine, immutable evidence, HMAC + mTLS | Connector-specific security review |
| Unauthorized cross-domain inference | fail-closed document/project/area ACLs | Periodic authorization tests |
| Audit tampering/exfiltration | admin-only export, redaction, export hash chain, retention policy | DB/WORM/SIEM controls and external log retention |
| Destructive migration/DDL abuse | one-shot migrator role; runtime role without DDL | DBA-enforced grants and negative test |
| Secret leakage in repository | deterministic secret scanner, no real TLS/private keys in repository | Corporate secret manager and rotation |

## Explicit non-claims
v6.0.5 does not claim formal certification, penetration-test completion, zero CVEs, SOC 2/ISO 27001 compliance, or cryptographic non-repudiation of database audit rows. Those require external controls and independent evidence.
