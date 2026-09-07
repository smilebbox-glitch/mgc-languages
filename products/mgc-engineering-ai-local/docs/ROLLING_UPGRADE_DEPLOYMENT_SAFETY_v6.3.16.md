# MGC Engineering AI Local v6.3.16 — Rolling Upgrade & Deployment Safety

## Goal

Allow controlled patch-level upgrades without letting an incompatible API/worker pair silently execute engineering side effects, without killing active long-running CAD/RAG/document jobs, and without allowing two Celery Beat schedulers to publish the same periodic work.

This release changes **application runtime behavior only**. Database schema remains `6.3.13`.

## Runtime compatibility window

Every new Celery publication carries:

- `mgc_app_version`;
- `mgc_schema_version`;
- `mgc_deployment_profile`.

Workers validate that envelope before entering the task body. Compatibility requires:

1. identical database schema version;
2. identical major/minor application version;
3. patch-version difference no greater than `ROLLING_UPGRADE_MAX_PATCH_SKEW` (default `1`).

Therefore `6.3.15 ↔ 6.3.16` with schema `6.3.13` is the intended transition window. `6.3.14 ↔ 6.3.16` or any schema mismatch fails closed.

Legacy queue messages created before v6.3.16 do not contain this envelope. `ROLLING_UPGRADE_ALLOW_LEGACY_TASK_ENVELOPES=true` exists only for the controlled transition from v6.3.15. After the old queue backlog is retired, corporate configuration should set it to `false`.

## Worker drain

Workers now use role-prefixed node names:

- `interactive@<container>`;
- `cpu@<container>`;
- `io@<container>`;
- `cad@<container>`;
- `ai@<container>`.

`python -m app.workers.drain_cli --prefix <role>@` first cancels queue consumers for the selected worker and then waits until its active task list reaches zero. The default Docker stop grace period is 10 minutes. The rollout script does **not** use SIGKILL as a normal upgrade mechanism.

This is important for native CAD conversion, document ingestion and other jobs that can legitimately run for minutes. If drain times out, rollout stops instead of intentionally duplicating the work.

## Scheduler single-leader rule

`beat` now starts through `python -m app.workers.singleton_beat`.

The wrapper owns a PostgreSQL session-level advisory lock for the full Beat lifetime. A second Beat instance remains `standby`. The lock-owning database session is periodically probed; loss of that session terminates the publishing Beat fail-closed because the advisory lock can no longer prove leadership.

PostgreSQL is used here only as the coordination authority already required by Core. No Redis distributed lock is treated as engineering truth.

## Deployment component registry

API, workers and Beat publish short-lived runtime heartbeats to Redis containing only:

- component type and node identifier;
- application version;
- schema version;
- deployment profile;
- operational state (`active`, `draining`, `standby`).

The registry is ephemeral diagnostics. Redis outage does not block deterministic Core access. However, if the registry is available and a **known incompatible** component is present, `/api/v1/health/ready` fails closed.

Engineering Admin can inspect:

`GET /api/v1/operations/deployment-safety`

Prometheus exposes runtime-skew/component gauges, and the privacy-safe support bundle includes `deployment-safety.json`.

## Controlled upgrade order

For v6.3.15 → v6.3.16 the certified source workflow is:

1. run static rollout preflight and Compose validation;
2. drain and replace workers one resource class at a time;
3. replace Beat after worker fleet compatibility is established;
4. replace API only after new workers are available;
5. require API readiness before presentation-layer replacement;
6. replace frontend and gateway;
7. review Deployment Safety and Operations status;
8. leave Production GO to the corporate human change-approval process.

Run:

```bash
make rolling-upgrade-preflight
make rolling-upgrade
```

The script assumes the target v6.3.16 images have already been built/imported under the configured image names. It does not fabricate registry artifacts or authorize production.

## Explicit non-goals

v6.3.16 does not claim:

- zero-downtime API replacement on a single-node Docker Compose deployment;
- Kubernetes/Swarm rolling-update semantics;
- live PostgreSQL schema migration during mixed-version operation;
- compatibility across arbitrary major/minor versions;
- safe forced termination of active engineering jobs;
- production authorization based only on runtime health.

For clustered production, the same task-envelope, worker-drain, scheduler-leader and version-skew invariants should be enforced by the corporate orchestrator/load balancer.
