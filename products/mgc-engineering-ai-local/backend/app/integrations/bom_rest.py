from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .base import ExternalAsset, SyncPage
from .http_common import HttpConnectorBase


class BomRestConnector(HttpConnectorBase):
    connector_type = "bom_rest"

    def list_assets(self, cursor: str | None = None, limit: int = 100) -> SyncPage:
        path = self.config.get("list_path", "/api/boms")
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = self.request("GET", path, params=params).json()
        items = data.get("items", [])
        assets = []
        for row in items:
            pn = str(row.get("part_number") or row.get("parent_part_number") or "")
            rev = row.get("revision")
            ext_id = str(row.get("id") or f"{pn}:{rev or ''}")
            assets.append(ExternalAsset(
                external_id=ext_id,
                name=f"{pn}_{rev or 'NA'}_bom.csv",
                kind="bom",
                revision=rev,
                part_number=pn or None,
                modified_at=row.get("modified_at"),
                metadata=row,
            ))
        return SyncPage(assets, data.get("next_cursor"), data.get("checkpoint"))

    def fetch_asset(self, asset: ExternalAsset, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        path = self.config.get("detail_path_template", "/api/boms/{external_id}").format(external_id=asset.external_id)
        payload = self.request("GET", path).json()
        rows = payload.get("items", payload if isinstance(payload, list) else [])
        target = target_dir / asset.name
        with target.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["part_number", "revision", "quantity", "description"])
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "part_number": row.get("part_number") or row.get("child_part_number"),
                    "revision": row.get("revision") or row.get("child_revision") or "",
                    "quantity": row.get("quantity", 1),
                    "description": row.get("description") or row.get("name") or "",
                })
        return target
