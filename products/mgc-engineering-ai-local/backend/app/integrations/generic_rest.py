from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .base import ExternalAsset, SyncPage
from .http_common import HttpConnectorBase


class GenericEngineeringRestConnector(HttpConnectorBase):
    """Vendor-neutral contract for PLM/PDM/ERP/MES/QMS gateways.

    Expected endpoint shapes are configurable so an internal integration layer can
    map Teamcenter/Windchill/3DEXPERIENCE/SAP/etc. without coupling the core app.
    """

    connector_type = "engineering_rest"

    def list_assets(self, cursor: str | None = None, limit: int = 100) -> SyncPage:
        path = self.config.get("list_path", "/api/assets")
        cursor_param = self.config.get("cursor_param", "cursor")
        limit_param = self.config.get("limit_param", "limit")
        params = {limit_param: limit}
        if cursor:
            params[cursor_param] = cursor
        payload = self.request("GET", path, params=params).json()
        items = payload.get(self.config.get("items_key", "items"), [])
        next_cursor = payload.get(self.config.get("next_cursor_key", "next_cursor"))
        checkpoint = payload.get(self.config.get("checkpoint_key", "checkpoint"))
        assets = [self._map_asset(x) for x in items]
        return SyncPage(assets=assets, next_cursor=str(next_cursor) if next_cursor is not None else None, checkpoint=str(checkpoint) if checkpoint is not None else None)

    def _map_asset(self, item: dict[str, Any]) -> ExternalAsset:
        f = self.config.get("field_map", {})
        def field(name: str, default: str | None = None):
            return item.get(f.get(name, name), default)
        return ExternalAsset(
            external_id=str(field("external_id") or field("id")),
            name=str(field("name") or field("filename") or field("external_id") or "asset.bin"),
            kind=str(field("kind", "document")),
            revision=field("revision"),
            part_number=field("part_number"),
            project_code=field("project_code"),
            modified_at=str(field("modified_at") or "") or None,
            checksum=field("checksum"),
            metadata=item,
            download_url=field("download_url"),
        )

    def fetch_asset(self, asset: ExternalAsset, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        record_mode = bool(self.config.get("record_mode") or self.config.get("inline_record"))
        safe_name = Path(asset.name).name
        if record_mode and not Path(safe_name).suffix:
            safe_name += ".json"
        target = target_dir / safe_name
        if record_mode:
            target.write_text(json.dumps(asset.metadata or {}, ensure_ascii=False, sort_keys=True, indent=2, default=str), encoding="utf-8")
            return target
        if asset.download_url:
            if asset.download_url.startswith("http://") or asset.download_url.startswith("https://"):
                r = self.client.get(asset.download_url, headers=self.auth_headers())
                r.raise_for_status()
            else:
                r = self.request("GET", asset.download_url)
        else:
            template = self.config.get("download_path_template", "/api/assets/{external_id}/content")
            path = template.format(external_id=quote(asset.external_id, safe=""))
            r = self.request("GET", path)
        target.write_bytes(r.content)
        return target
