from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ExternalAsset:
    external_id: str
    name: str
    kind: str
    revision: str | None = None
    part_number: str | None = None
    project_code: str | None = None
    modified_at: str | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    download_url: str | None = None
    local_path: str | None = None
    content: bytes | None = None


@dataclass(slots=True)
class ConnectorHealth:
    ok: bool
    message: str
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SyncPage:
    assets: list[ExternalAsset]
    next_cursor: str | None = None
    checkpoint: str | None = None


class Connector(Protocol):
    connector_type: str

    def health(self) -> ConnectorHealth: ...
    def list_assets(self, cursor: str | None = None, limit: int = 100) -> SyncPage: ...
    def fetch_asset(self, asset: ExternalAsset, target_dir: Path) -> Path: ...


class ConnectorError(RuntimeError):
    pass
