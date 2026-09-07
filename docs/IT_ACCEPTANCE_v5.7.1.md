# MGC Languages v5.7.1 — IT Acceptance Addendum

v5.7 acceptance remains mandatory. v5.7.1 adds these checks.

## Database observability
1. `GET /api/admin/database/telemetry` is Admin-only.
2. Confirm query timing and PostgreSQL pool data are visible.
3. Confirm slow-query items expose fingerprint/operation/timing only — no SQL text or bind parameters.
4. Under representative load, check pool saturation remains below the agreed threshold.
5. Route Prometheus/OpenTelemetry to the corporate monitoring stack if available.

## Backup / recovery evidence
1. Confirm `backup` service produces `.dump` + `.sha256` in the approved pilot backup path.
2. Run `scripts/restore_rehearsal.sh backups/<dump>` against the isolated temporary DB flow.
3. Confirm a `*.restore-ok.json` file is produced with `duration_seconds`.
4. Run `python scripts/recovery_evidence_check.py`.
5. Confirm `/api/admin/recovery/evidence` and IT Dashboard show current evidence.
6. Compare measured restore duration with agreed pilot RTO.
7. Do not sign off production DR until backup/WAL is encrypted and stored outside the app host/failure domain.

## Failure drill
On an approved sandbox/pilot window only:
```bash
CONFIRM_PILOT_DRILL=YES bash scripts/postgres_failure_drill.sh
```
Expected result:
- during DB pause: `/health/live` = 200, `/health/ready` = 503;
- after resume: readiness returns to 200;
- no internal DB details are returned to the end user.

## Sign-off boundary
Passing v5.7.1 confirms pilot observability/recovery controls, not a contractual SLA or production HA/DR certification.
