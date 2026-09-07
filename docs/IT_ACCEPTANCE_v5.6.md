# IT Acceptance v5.6

## Automated gates
- application version `5.6`;
- readiness `ready`;
- Alembic current/head `b56f0c21e560`;
- voice recording disabled;
- protected metrics;
- Chinese learning standard = Putonghua;
- dialect content reference-only;
- Admin governance endpoints available;
- pilot group create/member/feature/assignment flow works;
- CSV export works;
- IT Dashboard/SLO/alerts remain available;
- Mandarin WAV or documented browser fallback;
- quota configuration passes preflight.

## Real infrastructure evidence still required
- actual corporate OIDC claims/groups/department mapping;
- TLS + secure cookie policy;
- PostgreSQL backup and isolated restore rehearsal;
- central monitoring/SIEM ingestion;
- vulnerability/container scanning per corporate policy;
- pilot owner approval of group membership and exported-data handling.

## Governance reversibility checks
- Admin can remove a pilot member without deleting the user.
- Admin can remove an accidental track assignment without deleting learning history.
- Both privileged changes are auditable.
- Overlapping active groups use deny-wins semantics for explicit feature overrides.
- Future-dated groups do not affect current feature access.
