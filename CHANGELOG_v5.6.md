# MGC Languages v5.6 — Pilot Governance & Rollout

## User clarity
- Chinese learning scope is explicit across every core Chinese learning screen: **Путунхуа (普通话) — standard Chinese**.
- Sidebar entry is now **«Информация о китайском»**.
- Dialect/regional content is marked **reference-only** and does not award XP, affect the course, tests, final exam or Skills Matrix.
- Chinese language switch reads `中文 · Путунхуа`.
- Pilot-assigned Chinese tracks are labelled as Putonghua.

## Pilot governance
- Pilot groups with department, rollout wave and lifecycle status (`draft / active / paused / completed`).
- Explicit group membership managed by Admin and fully audited.
- Feature flags with per-group rollout overrides.
- Built-in flags: games, XP economy, learning nudges, Chinese reference, server audio, AI assistant.
- Group-level learning-track assignments with language, target level and optional due date.
- Employee `/api/pilot/me` view returns current wave, assignments, effective feature flags and quota policy.
- Admin CSV export for all pilot users or one rollout group.

## Abuse / quota controls
- Bounded per-user daily counters for XP awards, game starts, TTS and practice submissions.
- Daily usage is retained for a bounded configurable period and included in maintenance cleanup.
- Quota values are environment-driven and validated by pilot preflight.

## Database / IT
- New Alembic head: `b56f0c21e560`.
- New tables: `pilot_groups`, `pilot_group_members`, `feature_flags`, `pilot_group_features`, `pilot_track_assignments`, `pilot_daily_usage`.
- Pilot Compose image tag updated to `mgc-languages:5.6-it`.
- Existing SLO, alerts, recovery-state machine, retention, TTS privacy, CSRF/RBAC and schema-readiness remain intact.

## v5.6 final hardening
- Rollout groups can be edited after creation, including status, wave number, start/end dates, department and description.
- Scheduled waves are inactive before `starts_at` and after `ends_at`; paused/completed groups do not grant rollout access.
- Overlapping group feature overrides use conservative **deny-wins** semantics.
- Admin UI supports rollout scheduling, status changes, member removal, feature toggles and track assignments without manual API calls.
- Employee home screen shows the active pilot cohort/wave.
- CSV export separates English and Chinese Putonghua progress fields.
- Duplicate practice submissions with the same idempotent session id no longer consume daily practice quota twice.
- `pilot_daily_usage` receives configurable retention cleanup (`PILOT_USAGE_RETENTION_DAYS`, default 90 days).

### Rollout administration hardening
- Admin rollout UI now edits wave status/start/end dates, adds/removes members and toggles group feature flags without manual API calls.
- Learning-track assignment captures topic and due date; an accidental assignment can be removed from the UI/API.
- Assignment removal is written to the privileged Audit Log.
- Regression execution is split into isolated CI shards (base, pronunciation, Putonghua/schema, reliability, operations/governance) with per-test timeouts to prevent TTS/TestClient resource leakage from hiding later results.
