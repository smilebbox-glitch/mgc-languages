# v5.9.7 — User Login & Department Onboarding

## Added

- department field in local registration/login browser UI;
- automotive department dropdown for tomorrow's office pilot;
- registration persists the selected department on the existing User model;
- local login verifies a supplied department for non-admin users;
- admin remains password/role based so a department typo cannot lock out administration;
- `static/auth_department.js` layers the new browser payload without rewriting the large legacy frontend bundle;
- explicit LAN admin credential synchronization before Uvicorn workers start;
- `MGC_ADMIN_DEPARTMENT` and `MGC_ADMIN_SYNC_CREDENTIALS` LAN settings;
- first-run Windows launcher prompt for the admin password;
- v597 regression shard and focused Docker LAN gate;
- tomorrow-test runbook.

## Compatibility

- no ORM/Alembic schema change; User.department already existed;
- API clients that omit department remain compatible;
- browser UI requires department;
- OIDC behavior is unchanged and continues to source department from the configured claim;
- XP/SRS/games/terminology/content and Путунхуа (普通话) are unchanged;
- runtime APP_VERSION is intentionally unchanged.

## Security

- no real admin password is committed to the repository;
- LAN password is stored only in local `.env.lan`;
- admin sync is explicit and production requires the additional `ALLOW_ADMIN_CREDENTIAL_RESET=true` guard.
