# Pilot Governance Runbook v5.6

## Recommended rollout
1. Create a pilot group for one department/function.
2. Assign a rollout wave (`1`, `2`, ...).
3. Keep group `draft` until IT/business owner approves scope.
4. Add named pilot users.
5. Configure feature overrides only where needed; avoid multiple conflicting groups for one user.
6. Assign learning tracks (English or Putonghua/Chinese) and target level.
7. Change the group to `active`.
8. Observe SLO/alerts, learning-error telemetry and group CSV results.
9. Pause the group if a material issue is found; feature access is recalculated immediately.
10. Mark `completed` when evaluation is closed.

## Feature flags
Built-in keys:
- `games`
- `xp_economy`
- `learning_nudges`
- `chinese_reference`
- `server_audio`
- `ai_assistant`

A group override controls optional features, not user competency data. Disabling a feature must never erase progress.

## Daily quotas
Defaults:
- XP award: 2500/day/user
- game starts: 150/day/user
- server TTS: 500/day/user
- practice submissions: 300/day/user

These are anti-abuse ceilings, not learning targets. Normal users should never be encouraged to reach them.

## Export
Admin can export UTF-8 CSV globally or by group. Export contains identifiers, department, role, level, XP activity, term coverage and last activity. Treat exports as internal corporate data and store according to approved retention/access policy.

## Scheduling and overlap rules
- A wave may have `starts_at` and `ends_at`; an `active` group is effective only inside that time window.
- `draft`, `paused` and `completed` groups do not grant rollout access.
- If a user belongs to several currently effective groups and the same feature is explicitly enabled in one but disabled in another, **disabled wins**. This is intentional fail-closed rollout behavior.
- Prefer one primary pilot group per employee; use overlaps only for controlled cross-functional cases.

## Idempotency and retention
- A repeated practice submission with the same `session_id` is treated as the same event and does not consume the practice quota again.
- Daily pilot-usage counters are retained for `PILOT_USAGE_RETENTION_DAYS` (default 90) and removed by the maintenance workflow.

## Export fields
The v5.6 CSV separates `english_known/touched` from `chinese_putonghua_known/touched`, so reporting cannot accidentally describe dialect-reference viewing as Chinese-course progress.

## Correcting rollout configuration
- Admin can change a group's `draft/active/paused/completed` status, wave number, start date and end date from the Pilot Governance screen.
- A member can be removed from a group immediately; effective feature access is recalculated on the next request.
- Track assignments include optional professional topic and due date.
- If a track was assigned by mistake, use **Снять назначение**. The deletion is audited as `pilot.assignment.delete`; learning progress itself is not deleted.
