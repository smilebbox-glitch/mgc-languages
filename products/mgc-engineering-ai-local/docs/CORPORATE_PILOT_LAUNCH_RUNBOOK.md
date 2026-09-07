# Corporate Pilot Launch Runbook — v6.1.0

## 1. Freeze release
Verify ZIP SHA-256, SBOM, dependency locks/wheelhouse, image digests and approved change ticket.

## 2. Prepare infrastructure
Apply sizing profile, protected SSD storage, backup target, DNS/NTP, internal network and default-deny firewall rules.

## 3. Identity/security
Deploy enterprise-security overlay, TLS/mTLS certificates, OIDC/AD integration and distinct PostgreSQL migration/runtime identities. Run negative tests and CVE scan.

## 4. Build and start
On approved build host:

```bash
docker compose build
make dockle
make acceptance
make corporate-deployment-preflight
```

For enterprise runtime use the air-gap/runtime + SSO + webhooks + enterprise-security overlays documented in the project.

## 5. Connect sources
Connect one project and read-only gateways in controlled order: PLM/PDM -> ERP/BOM -> MES -> QMS -> native CAD gateway as applicable. Run Data Confidence and reconciliation after each source.

## 6. Prove recoverability/operations
Run backup->restore drill, observability checks and Operations Game Day rehearsal.

## 7. Evaluate launch readiness
Use `POST /api/v1/deployment/readiness` with evidence from the real target host. `READY_TO_LAUNCH_CONTROLLED_PILOT` means only that the controlled pilot may begin after human change approval.

## 8. Roll out users
Follow `CORPORATE_PILOT_ROLLOUT_PLAN.md`; do not begin with the full company.
