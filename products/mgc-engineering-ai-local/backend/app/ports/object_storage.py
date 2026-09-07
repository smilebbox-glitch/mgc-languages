from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStoragePort(Protocol):
    """Optional evidence-mirroring contract.

    PostgreSQL + local evidence storage remain authoritative for Core. An
    adapter may mirror immutable evidence to an external object store.
    """

    mode: str

    def mirror_file(self, path: Path, object_name: str) -> dict | None: ...
