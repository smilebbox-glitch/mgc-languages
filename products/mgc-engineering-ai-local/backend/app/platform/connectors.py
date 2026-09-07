from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.integrations.base import ExternalAsset

CONNECTOR_ENVELOPE_SCHEMA = "mgc-connector-envelope-v1"

@dataclass(frozen=True, slots=True)
class EngineeringEnvelope:
    source: str
    entity_type: str
    external_id: str
    revision: str | None
    source_timestamp: str | None
    project_code: str | None
    part_number: str | None
    payload: dict[str, Any]

    def public(self) -> dict[str, Any]:
        return {"schema": CONNECTOR_ENVELOPE_SCHEMA, **asdict(self)}


def asset_to_envelope(source: str, asset: ExternalAsset) -> EngineeringEnvelope:
    return EngineeringEnvelope(
        source=source,
        entity_type=(asset.kind or "document").lower(),
        external_id=asset.external_id,
        revision=asset.revision,
        source_timestamp=asset.modified_at,
        project_code=asset.project_code,
        part_number=asset.part_number,
        payload={"name": asset.name, "checksum": asset.checksum, **dict(asset.metadata or {})},
    )


def connector_contract() -> dict[str, Any]:
    return {
        "schema": CONNECTOR_ENVELOPE_SCHEMA,
        "sdk": ["health", "list_assets/discover", "fetch_asset/fetch", "checkpoint"],
        "canonical_envelope": ["source", "entity_type", "external_id", "revision", "source_timestamp", "project_code", "part_number", "payload"],
        "source_system_remains_authoritative": True,
    }
