# Changelog v5.7 — Security & Data Integrity

## Security
- PostgreSQL FORCE RLS policies for user-owned learning data.
- Request transaction receives user/role/department RLS context after authentication.
- Readiness/preflight can require RLS and terminology approval.
- Expanded role/department negative authorization test matrix.
- Audit Log SHA-256 chain and verification endpoint.

## Content integrity
- Custom-term provenance fields.
- Full immutable term revisions.
- Editor review workflow; Admin approve/reject/rollback.
- Imports create revisions and default to review-oriented governance.

## Adaptive learning
- Persistent SRS cards with lapses, repetitions, ease and due date.
- Due-review queue and review-result API.
- Question-attempt telemetry stores selected-answer hash only.
- Admin/Editor question-quality analytics.

## Observability / recovery
- Optional OpenTelemetry FastAPI + SQLAlchemy traces.
- Grafana dashboard and Prometheus alert rule templates.
- SRS/question-attempt Prometheus metrics.
- WAL archiving / PITR rehearsal configuration and base-backup helper.

## Release hardening
- Added a 56-check role/endpoint/department authorization matrix.
- Fixed retention cleanup for timezone-aware audit rows by forcing SQL-side delete synchronization; reliability regression covers the path.
- `postgres_rls_check.py` now rejects superuser/BYPASSRLS application DB roles and validates identity-bearing policy expressions.
- CI split into independent regression matrix jobs; static/schema checks are separate from TTS/TestClient regression.
- Corrected Prometheus database-metrics alert naming so it does not imply backup verification.
