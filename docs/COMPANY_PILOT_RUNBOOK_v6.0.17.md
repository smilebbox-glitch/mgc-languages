# MGC Language Lab — Company Pilot Runbook v6.0.17

## Status

This branch is a **controlled company pilot candidate**, not a production release. The intended first wave is 5–10 employees plus 1 admin and 1–2 managers.

## Pilot scope

- Chinese language track for automotive work.
- English language track for automotive work.
- Daily phrase rotates deterministically by calendar day on every client.
- Daily illustration rotates between 7 local/offline factory scenes.
- Topics, quizzes, roleplay, 30-day course, games, XP, final assessment.
- Manager team progress.
- Admin analytics, content governance, pilot governance and IT operations.
- PostgreSQL, Nginx, backup job and maintenance service from `docker-compose.pilot.yml`.

## Pilot cohort

Recommended Wave 1:

| Role | Count | Suggested functions |
|---|---:|---|
| User | 5–10 | R&D, Quality, Production, Logistics, Procurement |
| Manager | 1–2 | Team leads for participating departments |
| Editor | 1 | Training/content owner if required |
| Admin | 1 | IT/product pilot administrator |

Do not use personal production accounts until IT approves OIDC, TLS, retention and backup settings.

## 1. Server preparation

Minimum controlled pilot assumptions:

- Linux host with Docker Engine and Docker Compose v2.
- Stable LAN DNS name or static IP.
- Employees can reach the selected TCP port.
- Persistent disk for PostgreSQL and `./backups`.
- Corporate OIDC client and TLS termination are preferred for the company pilot.

Create the environment file:

```bash
cp .env.company-pilot.example .env.pilot
chmod 600 .env.pilot
```

Replace every `CHANGE_ME` value. Set the real pilot DNS name in `TRUSTED_HOSTS`. Never commit `.env.pilot`.

## 2. Configuration gate

Run before starting the pilot:

```bash
python scripts/company_pilot_preflight.py \
  --env-file .env.pilot \
  --strict-corporate
```

Expected result: `GO`.

Any `NO-GO` is a launch blocker until explicitly resolved by IT/security.

## 3. Build and start

```bash
docker compose \
  --env-file .env.pilot \
  -f docker-compose.pilot.yml \
  build

docker compose \
  --env-file .env.pilot \
  -f docker-compose.pilot.yml \
  up -d
```

Do **not** use `docker compose down -v` during the pilot; it removes persistent database volumes.

## 4. Runtime gate

From the pilot server or an allowed admin workstation:

```bash
python scripts/company_pilot_preflight.py \
  --env-file .env.pilot \
  --strict-corporate \
  --url https://mgc-language-pilot.company.local
```

Required endpoints:

- `/health/live` → 2xx
- `/health/ready` → 2xx
- `/api/meta` → 2xx

Check containers:

```bash
docker compose --env-file .env.pilot -f docker-compose.pilot.yml ps
```

All long-running services must be healthy/running.

## 5. Identity and role validation

Before inviting ordinary users, validate one account for each enabled role:

1. User can access only learning surfaces.
2. Manager can access only the manager/team scope for the permitted department.
3. Editor can access content governance but not user analytics/pilot IT controls.
4. Admin can access analytics, content governance, pilot governance and IT operations.
5. A user without an authorized role cannot open manager/admin endpoints by direct URL/API calls.

OIDC group mapping is configured with:

- `OIDC_ADMIN_GROUP`
- `OIDC_EDITOR_GROUP`
- `OIDC_MANAGER_GROUP`
- `OIDC_DEPARTMENT_CLAIM`

## 6. Approved pilot UI baseline

The pilot home page has two approved variants using the same component system:

### Chinese language

- Russian UI chrome.
- Hero: `Китайский язык для автопрома`.
- Daily phrase: Chinese + Pinyin + Russian translation.
- `Информация о китайском` is visible only for the Chinese track.

### English

- Russian UI chrome.
- English hero copy is allowed.
- Daily phrase content is English.
- No `About English` sidebar item.

The home page intentionally does not show the old pilot-wave strip, duplicate quick cards or a left-sidebar notifications item.

## 7. Daily phrase behavior

`static/frontend/pilot_home.js` chooses the phrase from the calendar date. This makes the same phrase appear on all employee PCs on the same day without a database write or external service.

- Phrase changes after local midnight.
- A midnight timer refreshes the home screen if it is open.
- Illustration changes daily using `/static/pilot/phrase-1.svg` … `/phrase-7.svg`.
- All artwork is local/offline; no public CDN or tracking pixel is required.

## 8. UAT before inviting Wave 1

Run `docs/PILOT_UAT_v6.0.17.md` with at least:

- one User;
- one Manager;
- one Admin;
- Chinese language;
- English language;
- two separate PCs on the company LAN.

No Severity 1 or Severity 2 UAT defect may remain open at launch.

## 9. First-wave operating schedule

### Day 0 — IT validation

- Preflight = GO.
- Backup job creates a valid backup + checksum.
- Admin/manager/user permissions verified.
- Browser smoke on two PCs.

### Day 1 — 3 users

Invite three users only. Confirm login, progress persistence, audio, phrase of day, quizzes and roleplay.

### Days 2–3 — 5–10 users

Add the remaining Wave 1 participants if there are no S1/S2 incidents.

### Day 5 — checkpoint

Review:

- active users;
- sessions and errors;
- weak topics/question quality;
- user feedback;
- DB/HTTP/TTS alerts;
- backup evidence.

### Day 10 — pilot decision

Choose one:

- `GO`: expand next wave;
- `GO WITH ACTIONS`: continue current cohort with tracked non-critical fixes;
- `NO-GO`: stop onboarding and return to remediation.

## 10. Success criteria

Minimum pilot acceptance:

- 100% of invited accounts can authenticate or have a documented identity-system reason.
- No cross-user or cross-department data leak.
- No loss of progress after browser/server restart.
- Chinese and English home pages render correctly on supported browsers.
- Daily phrase changes on a new calendar day.
- Core learning path completes: topic → quiz → scenario → XP/progress.
- Final assessment saves a result.
- Manager scope is department-safe.
- Admin dashboards load without exposing secrets/raw sensitive telemetry.
- Backup evidence exists and a restore rehearsal is current per configured policy.
- No unresolved S1/S2 incident.

## 11. Incident handling

For an application incident:

```bash
docker compose --env-file .env.pilot -f docker-compose.pilot.yml logs --tail=300 app nginx db
```

If necessary, stop employee access at Nginx while preserving PostgreSQL and backups. Do not delete volumes.

For suspected data-access/security issues, immediately stop onboarding, preserve logs/audit evidence and escalate to IT/security. Do not attempt to conceal or purge evidence.

## 12. Rollback

A rollback is a controlled deployment action, not a database deletion.

1. Stop new onboarding.
2. Take an on-demand PostgreSQL backup.
3. Deploy the last approved pilot image/commit.
4. Keep the same persistent database unless a reviewed schema/data rollback plan explicitly requires otherwise.
5. Re-run readiness and UAT smoke before reopening access.

## Launch authority

Technical `GO` from the script is necessary but not sufficient. Final company launch requires the named IT/service owner to confirm identity, network/TLS, backup, retention and user-cohort readiness.
