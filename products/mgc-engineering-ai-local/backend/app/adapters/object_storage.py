from __future__ import annotations

from pathlib import Path


class NoOpObjectStorageAdapter:
    mode = "local_evidence_only"

    def mirror_file(self, path: Path, object_name: str) -> dict | None:
        return None


class MinioObjectStorageAdapter:
    mode = "minio_mirror"

    def mirror_file(self, path: Path, object_name: str) -> dict | None:
        from app.services.object_store import mirror_file
        return mirror_file(path, object_name)
