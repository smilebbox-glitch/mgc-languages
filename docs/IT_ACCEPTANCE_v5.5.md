# MGC Languages v5.5 — IT Pilot Acceptance

## Static release gate
Run:
```bash
bash scripts/static_preflight.sh
```
Expected final line:
`PASS: v5.5 static pilot preflight`

## Clean schema gate
Expected Alembic head:
`a55c0b91d550`

Verify on a clean pilot database:
```bash
AUTO_CREATE_SCHEMA=false DATABASE_URL=<pilot-db> alembic upgrade head
AUTO_CREATE_SCHEMA=false DATABASE_URL=<pilot-db> alembic current
```

## Runtime acceptance
After deployment:
```bash
MGC_BASE_URL=https://<pilot-host> \
METRICS_TOKEN=<token> \
python scripts/it_acceptance_v55.py --report IT_ACCEPTANCE_REPORT_v5.5.md
```

For local-auth technical sandbox also provide:
`MGC_ADMIN_USERNAME` and `MGC_ADMIN_PASSWORD`.

## Required checks
1. `/health/live` returns v5.5.
2. `/health/ready` is ready and schema head is `a55c0b91d550`.
3. Self-registration is disabled in pilot.
4. Metrics are protected by bearer token.
5. No microphone capability is enabled.
6. Chinese foundations title is `Информация о китайском`.
7. Putonghua overview still contains ten **major groups**, not a claim of ten total local dialects.
8. Dialect comparison cards include Putonghua plus selected regional pronunciation examples.
9. Regional examples do not invoke fake Mandarin-generated dialect audio.
10. `/api/admin/it-dashboard` exposes readiness, recovery, SLO and alerts.
11. `/api/admin/learning-error-telemetry` is Admin-only and aggregated.
12. Alert acknowledgement is audit-logged.
13. Prometheus output includes v5.5 SLO/recovery/alert metrics.
14. Maintenance dry-run reports retention backlog without deleting data.
15. PostgreSQL failure drill yields controlled 503/not-ready behavior.
16. Offline TTS failure degrades to browser fallback without blocking core learning.
17. Backup + isolated restore rehearsal is completed by IT on real PostgreSQL.
18. OIDC/department claim mapping is validated against the corporate IdP before controlled-user rollout.

## Sign-off boundary
Passing this checklist means “acceptable for controlled pilot under the approved pilot boundary”. It is not unconditional production sign-off or a contractual SLA declaration.
