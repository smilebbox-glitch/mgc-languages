from __future__ import annotations

import os
from typing import Any

from .bom_rest import BomRestConnector
from .cad_gateway import CadGatewayConnector
from .generic_rest import GenericEngineeringRestConnector
from .mounted_folder import MountedFolderConnector

_CONNECTORS = {
    "mounted_folder": MountedFolderConnector,
    "engineering_rest": GenericEngineeringRestConnector,
    "plm_rest": GenericEngineeringRestConnector,
    "pdm_rest": GenericEngineeringRestConnector,
    "erp_rest": GenericEngineeringRestConnector,
    "mes_rest": GenericEngineeringRestConnector,
    "qms_rest": GenericEngineeringRestConnector,
    "bom_rest": BomRestConnector,
    "cad_gateway": CadGatewayConnector,
}


def supported_connector_types() -> list[str]:
    return sorted(_CONNECTORS)


def _resolve_secret_refs(secret_refs: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (secret_refs or {}).items():
        if key.endswith("_env"):
            target_key = key[:-4]
            out[target_key] = os.getenv(str(value), "")
        else:
            # Non-secret connector parameters belong in config_json. Raw secrets are
            # deliberately ignored here so the API never has to persist credentials.
            out[key] = value if value in (None, "") else ""
    return out


def build_connector(connector_type: str, config: dict[str, Any], secrets: dict[str, Any] | None = None):
    cls = _CONNECTORS.get(connector_type)
    if not cls:
        raise ValueError(f"Unsupported connector type: {connector_type}")
    return cls(config, _resolve_secret_refs(secrets))
