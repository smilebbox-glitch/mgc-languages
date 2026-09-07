# Engineering Program Control — v5.4

## Purpose

v5.4 adds an engineering-program intelligence layer over the existing Digital Thread. It answers three operational questions without becoming a generic task tracker:

1. Which controlled engineering gate is next?
2. Which engineering dependencies and evidence gaps can block it?
3. If one milestone moves, which downstream engineering gates are exposed?

## Controlled inputs

Program Control reuses existing controlled records:

- Project milestones and manufacturing-area access;
- Launch Readiness checks and Launch Trials;
- Requirements and V&V evidence;
- PPAP and localization records;
- ECR/ECO and risk level;
- engineering risk register;
- production/process defects;
- change-effectiveness reviews and deviations;
- release baselines.

The only new storage object is `ProgramDependency`, a directed engineering milestone dependency with explicit lag and criticality.

## Dependency semantics

Only `finish_to_start` is supported in v5.4. A dependency is rejected if it would create a cycle. Both milestones must already be visible in the current Project/Manufacturing Area ACL context.

The displayed critical chain is based on deterministic due-date/dependency slack. It is intentionally **not** claimed to be formal CPM because the application does not own authoritative activity durations/resources.

## Gate forecast

The next configured Design Freeze, Release or SOP milestone is used as the target gate. If none exists, `Project.target_release_at` can be shown as a virtual target.

Forecast inputs are explicit:

- overdue milestones;
- dependency lag violations and propagated schedule exposure;
- incomplete required Launch Readiness items;
- high/critical residual engineering risks;
- high/critical open ECR/ECO;
- V&V not in passed/waived evidence state;
- PPAP not approved;
- open high/critical process defects;
- ineffective change reviews;
- expired deviations.

The forecast is GREEN / AMBER / RED and is advisory. It is not a probabilistic ML prediction and never approves a gate.

## What-if slip simulation

`POST /api/v1/projects/{project_code}/program-control/slip-simulation` accepts one visible milestone and an integer slip in days. The service propagates the delay through visible dependency lag relationships and returns affected downstream milestones.

The simulation never writes dates or status back to the database.

## Governance

Always true:

```json
{
  "advisory_only": true,
  "not_project_management_system_of_record": true,
  "not_plm_or_erp_or_mes": true,
  "no_automatic_gate_approval": true,
  "human_program_and_release_approval_required": true,
  "forecast_is_deterministic_not_probabilistic": true
}
```
