from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .base import ConnectorHealth, ExternalAsset, SyncPage


class MountedFolderConnector:
    connector_type = "mounted_folder"

    def __init__(self, config: dict[str, Any], secrets: dict[str, Any] | None = None):
        self.config = config or {}
        self.root = Path(self.config.get("path", "/integrations/share"))
        self.extensions = {x.lower() for x in self.config.get("extensions", [])}

    def health(self) -> ConnectorHealth:
        if not self.root.exists():
            return ConnectorHealth(False, f"Path does not exist: {self.root}")
        if not self.root.is_dir():
            return ConnectorHealth(False, f"Path is not a directory: {self.root}")
        return ConnectorHealth(True, "mounted folder available", details={"path": str(self.root)})

    def _files(self) -> list[Path]:
        files = [p for p in self.root.rglob("*") if p.is_file()]
        if self.extensions:
            files = [p for p in files if p.suffix.lower() in self.extensions]
        return sorted(files, key=lambda p: str(p).lower())

    def list_assets(self, cursor: str | None = None, limit: int = 100) -> SyncPage:
        offset = int(cursor or 0)
        files = self._files()
        page = files[offset:offset + limit]
        assets: list[ExternalAsset] = []
        for p in page:
            st = p.stat()
            rel = p.relative_to(self.root).as_posix()
            external_id = hashlib.sha256(rel.encode("utf-8")).hexdigest()
            assets.append(ExternalAsset(
                external_id=external_id,
                name=p.name,
                kind="file",
                modified_at=f"{st.st_mtime_ns}:{st.st_size}",
                metadata={"relative_path": rel, "size_bytes": st.st_size},
                local_path=str(p),
            ))
        next_offset = offset + len(page)
        return SyncPage(assets=assets, next_cursor=str(next_offset) if next_offset < len(files) else None)

    def fetch_asset(self, asset: ExternalAsset, target_dir: Path) -> Path:
        source = Path(asset.local_path or "")
        if not source.exists():
            raise FileNotFoundError(source)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        target.write_bytes(source.read_bytes())
        return target
