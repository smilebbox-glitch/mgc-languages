# MGC Languages v5.7 — IT Acceptance

This checklist is for a controlled corporate pilot. Local SQLite tests validate application behavior and migration shape; they do **not** prove PostgreSQL RLS, corporate SSO, TLS, backup durability or centralized observability.

## 1. Configuration gate
- Use PostgreSQL, not SQLite.
- Disable self-registration.
- Protect `/metrics` with a bearer token or private network policy.
- Configure explicit Trusted Hosts/CORS.
- Keep legacy GET TTS disabled and microphone prohibited.
- For corporate rollout, enable OIDC and Secure cookies after TLS is connected.

Run:
```bash
python scripts/pilot_preflight.py
python scripts/oidc_config_check.py
```

## 2. Schema / RLS
```bash
alembic upgrade head
python scripts/postgres_rls_check.py
```
Expected schema head: `c57d0a31f570`.

The application DB role must not be PostgreSQL superuser and must not have `BYPASSRLS`. Verify cross-department denial with real pilot identities after OIDC mapping is configured.

## 3. Runtime acceptance
```bash
MGC_BASE_URL=https://<pilot-host> \
METRICS_TOKEN=<token> \
AUTH_MODE=oidc \
python scripts/it_acceptance_v57.py --report docs/IT_ACCEPTANCE_REPORT_v5.7.md
```
For a local-auth sandbox only, supply the sandbox Admin credentials to the process.

## 4. Security/content review
- User cannot access Manager/Admin endpoints.
- Manager can read only own-department team statistics.
- Editor can author/review terminology but cannot approve/delete Admin-governed content.
- Admin approval/rollback and role changes appear in Audit Log.
- `GET /api/admin/audit/verify-chain` returns `ok=true`.
- Terminology provenance/source reference is populated for governed content.

## 5. Observability
- Import `deploy/observability/grafana-dashboard-v5.7.json`.
- Load `deploy/observability/prometheus-rules-v5.7.yml` according to corporate Prometheus policy.
- If traces are enabled, point `OTEL_EXPORTER_OTLP_ENDPOINT` to the approved collector and confirm trace export. Collector failure must not affect readiness.

## 6. Backup / recovery / PITR
```bash
bash scripts/backup_postgres.sh
bash scripts/restore_rehearsal.sh backups/<dump>
bash scripts/pitr_preflight.sh
bash scripts/pitr_basebackup.sh
```
Pilot same-host WAL storage is rehearsal-only. Before production approval, DBA must demonstrate off-host encrypted base backup + WAL retention, record RPO/RTO, and execute a timestamp-targeted recovery rehearsal.

## 7. Release evidence
- Static preflight PASS.
- All six independent regression shards PASS.
- Runtime acceptance PASS.
- Non-destructive load smoke PASS.
- Corporate OIDC/TLS/RLS/PITR/monitoring evidence attached to the change ticket.

## Acceptance boundary
Passing the included tests supports a controlled pilot; it is not a penetration test, legal SLA, HA certification, or unconditional production sign-off.
