from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import ConnectorHealth, ExternalAsset, SyncPage
from .http_common import HttpConnectorBase
from app.core.resilience import CircuitOpenError, circuit_allows, record_failure, record_success


_ALLOWED_TARGETS = {"auto", "step", "stp", "pdf", "dxf", "x_t", "stl", "txt", "csv", "xlsx"}


class CadGatewayConnector(HttpConnectorBase):
    """REST bridge to an approved native-CAD conversion service.

    The core never loads proprietary CAD SDKs. KOMPAS-3D/T-FLEX/CATIA/NX/etc.
    run in a separately licensed local gateway (typically Windows for KOMPAS
    and T-FLEX). Source bytes remain immutable in MGC; the derivative is hashed
    and ingested as a new evidence document.
    """

    connector_type = "cad_gateway"

    def capabilities(self) -> dict[str, Any]:
        return self.request("GET", self.config.get("capabilities_path", "/capabilities")).json()

    def health(self) -> ConnectorHealth:
        health = super().health()
        if not health.ok:
            return health
        try:
            health.details["capabilities"] = self.capabilities()
        except Exception as exc:
            health.details["capabilities_error"] = str(exc)
        return health

    def list_assets(self, cursor: str | None = None, limit: int = 100) -> SyncPage:
        return SyncPage([])

    def fetch_asset(self, asset: ExternalAsset, target_dir: Path) -> Path:
        raise NotImplementedError("CAD gateway is a converter, not an asset source")

    def convert(self, source_path: Path, target_format: str = "auto", target_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
        if not circuit_allows("native_cad"):
            raise CircuitOpenError("native_cad")
        requested = target_format.lower().lstrip(".")
        if requested not in _ALLOWED_TARGETS:
            raise ValueError(f"Unsupported conversion target: {target_format}")
        endpoint = self.config.get("convert_path", "/convert")
        try:
            with source_path.open("rb") as fh:
                r = self.request(
                    "POST",
                    endpoint,
                    data={"target_format": requested},
                    files={"file": (source_path.name, fh, "application/octet-stream")},
                )
        except Exception as exc:
            record_failure("native_cad", exc)
            raise
        record_success("native_cad")
        content_type = r.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = r.json()
            raise RuntimeError(payload.get("error") or "CAD gateway returned JSON instead of converted bytes")
        if not r.content:
            raise RuntimeError("CAD gateway returned an empty derivative")

        actual = (r.headers.get("X-CAD-Target-Format") or requested).lower().lstrip(".")
        if actual == "auto":
            raise RuntimeError("CAD gateway must return X-CAD-Target-Format when target_format=auto")
        if actual not in _ALLOWED_TARGETS - {"auto"}:
            raise RuntimeError(f"CAD gateway returned unsupported target format: {actual}")

        target_dir = target_dir or source_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (source_path.stem + "." + actual)
        target.write_bytes(r.content)
        metadata = {
            "gateway": self.base_url,
            "source_format": source_path.suffix.lower(),
            "requested_target_format": requested,
            "target_format": actual,
            "vendor": r.headers.get("X-CAD-Vendor") or self.config.get("vendor"),
            "document_kind": r.headers.get("X-CAD-Document-Kind"),
            "sdk": r.headers.get("X-CAD-SDK"),
            "sdk_version": r.headers.get("X-CAD-SDK-Version"),
            "gateway_build": r.headers.get("X-CAD-Gateway-Build"),
        }
        return target, metadata
