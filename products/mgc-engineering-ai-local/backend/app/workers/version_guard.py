from __future__ import annotations

from celery import Task

from app.core.deployment_safety import validate_task_headers


class VersionGuardedTask(Task):
    """Reject incompatible producer/consumer runtimes before the task body can mutate state."""

    abstract = True

    def __call__(self, *args, **kwargs):
        validate_task_headers(getattr(self.request, "headers", None))
        return super().__call__(*args, **kwargs)
