from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prometheus_client import Gauge

from app.db.models import ExternalObject, ExternalSystem
from app.integrations.base import ExternalAsset

CONTRACT_VERSION = "mgc-integration-v1"

INTEGRATION_CONFIDENCE = Gauge(
    "mgc_integration_data_confidence",
    "Current aggregate integration data confidence score (0..1)",
    ["system"],
)
INTEGRATION_QUARANTINE = Gauge(
    "mgc_integration_quarantine_events",
    "Outstanding quarantined integration events",
    ["system"],
)

SUPPORTED_SOURCE_DOMAINS = {"engineering", "plm", "pdm", "erp", "mes", "qms", "cad", "files"}
DEFAULT_REQUIRED_FIELDS = ("external_id", "name", "kind")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_source_timestamp(value: str | datetime | None) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def source_domain_for(system: ExternalSystem) -> str:
    explicit = (system.source_domain or "").strip().lower()
    if explicit in SUPPORTED_SOURCE_DOMAINS:
        return explicit
    prefix = (system.connector_type or "").split("_", 1)[0].lower()
    return prefix if prefix in SUPPORTED_SOURCE_DOMAINS else "engineering"


def contract_for(system: ExternalSystem) -> dict[str, Any]:
    cfg = system.config_json or {}
    nested = cfg.get("integration_contract") if isinstance(cfg.get("integration_contract"), dict) else {}
    required = system.required_fields or nested.get("required_fields") or list(DEFAULT_REQUIRED_FIELDS)
    required = [str(x).strip() for x in required if str(x).strip()]
    expected = system.expected_freshness_minutes
    if expected is None:
        raw = nested.get("expected_freshness_minutes")
        try:
            expected = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            expected = None
    allowed_kinds = nested.get("allowed_kinds") or cfg.get("allowed_kinds") or []
    return {
        "version": system.contract_version or CONTRACT_VERSION,
        "source_domain": source_domain_for(system),
        "required_fields": required,
        "expected_freshness_minutes": expected if expected and expected > 0 else None,
        "allowed_kinds": sorted({str(x).strip().lower() for x in allowed_kinds if str(x).strip()}),
        "max_future_clock_skew_minutes": int(nested.get("max_future_clock_skew_minutes", 10) or 10),
    }


def _field_value(asset: ExternalAsset, field: str) -> Any:
    builtin = {
        "external_id": asset.external_id,
        "name": asset.name,
        "kind": asset.kind,
        "revision": asset.revision,
        "part_number": asset.part_number,
        "project_code": asset.project_code,
        "modified_at": asset.modified_at,
        "checksum": asset.checksum,
        "download_url": asset.download_url,
    }
    if field in builtin:
        return builtin[field]
    path = field[9:] if field.startswith("metadata.") else field
    current: Any = asset.metadata or {}
    for piece in path.split("."):
        if not isinstance(current, dict) or piece not in current:
            return None
        current = current[piece]
    return current


def asset_snapshot(asset: ExternalAsset) -> dict[str, Any]:
    """Non-secret contract snapshot. Raw content/download credentials are never persisted."""
    return {
        "external_id": asset.external_id,
        "name": Path(asset.name or "asset.bin").name,
        "kind": asset.kind,
        "revision": asset.revision,
        "part_number": asset.part_number,
        "project_code": asset.project_code,
        "modified_at": asset.modified_at,
        "checksum": asset.checksum,
        "metadata": asset.metadata or {},
    }


def asset_from_snapshot(snapshot: dict[str, Any]) -> ExternalAsset:
    return ExternalAsset(
        external_id=str(snapshot.get("external_id") or ""),
        name=str(snapshot.get("name") or "asset.bin"),
        kind=str(snapshot.get("kind") or "document"),
        revision=snapshot.get("revision"),
        part_number=snapshot.get("part_number"),
        project_code=snapshot.get("project_code"),
        modified_at=snapshot.get("modified_at"),
        checksum=snapshot.get("checksum"),
        metadata=snapshot.get("metadata") or {},
    )


def validate_asset_contract(asset: ExternalAsset, contract: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not str(asset.external_id or "").strip() or str(asset.external_id).lower() in {"none", "null"}:
        errors.append({"code": "MISSING_EXTERNAL_ID", "field": "external_id"})
    raw_name = str(asset.name or "").strip()
    if not raw_name:
        errors.append({"code": "MISSING_NAME", "field": "name"})
    elif Path(raw_name).name != raw_name or raw_name in {".", ".."}:
        errors.append({"code": "UNSAFE_ASSET_NAME", "field": "name"})
    if not str(asset.kind or "").strip():
        errors.append({"code": "MISSING_KIND", "field": "kind"})

    required = contract.get("required_fields") or []
    present = 0
    missing: list[str] = []
    for field in required:
        value = _field_value(asset, field)
        if value not in (None, "", [], {}):
            present += 1
        else:
            missing.append(field)
    for field in missing:
        errors.append({"code": "REQUIRED_FIELD_MISSING", "field": field})

    allowed = set(contract.get("allowed_kinds") or [])
    if allowed and str(asset.kind or "").lower() not in allowed:
        errors.append({"code": "UNSUPPORTED_OBJECT_KIND", "field": "kind"})

    source_dt = None
    timestamp_contractual = bool(contract.get("expected_freshness_minutes")) or "modified_at" in set(required)
    if asset.modified_at:
        try:
            source_dt = parse_source_timestamp(asset.modified_at)
            skew_minutes = (source_dt - now).total_seconds() / 60.0 if source_dt else 0.0
            if skew_minutes > float(contract.get("max_future_clock_skew_minutes") or 10):
                target = errors if timestamp_contractual else warnings
                target.append({"code": "SOURCE_TIMESTAMP_IN_FUTURE", "field": "modified_at"})
        except (TypeError, ValueError):
            target = errors if timestamp_contractual else warnings
            target.append({"code": "INVALID_SOURCE_TIMESTAMP", "field": "modified_at"})
    elif contract.get("expected_freshness_minutes"):
        warnings.append({"code": "FRESHNESS_UNKNOWN", "field": "modified_at"})

    completeness = (present / len(required)) if required else 1.0
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "required_fields": required,
        "missing_fields": missing,
        "completeness": round(completeness, 4),
        "source_modified_at": source_dt.isoformat() if source_dt else None,
        "contract_version": contract.get("version") or CONTRACT_VERSION,
    }


def calculate_data_quality(asset: ExternalAsset, contract: dict[str, Any], validation: dict[str, Any], *, payload_sha256: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    source_dt = None
    try:
        source_dt = parse_source_timestamp(asset.modified_at)
    except (TypeError, ValueError):
        pass

    expected = contract.get("expected_freshness_minutes")
    if source_dt is None:
        freshness_status = "UNKNOWN" if expected else "NOT_CONFIGURED"
        freshness_score = 0.5 if expected else 1.0
        age_minutes = None
    else:
        age_minutes = max(0.0, (now - source_dt).total_seconds() / 60.0)
        if not expected:
            freshness_status, freshness_score = "OBSERVED", 1.0
        elif age_minutes <= expected:
            freshness_status, freshness_score = "FRESH", 1.0
        elif age_minutes <= expected * 2:
            freshness_status, freshness_score = "AGING", 0.7
        elif age_minutes <= expected * 4:
            freshness_status, freshness_score = "STALE", 0.4
        else:
            freshness_status, freshness_score = "STALE", 0.1

    schema_score = 1.0 if validation.get("valid") else 0.0
    completeness_score = float(validation.get("completeness", 0.0))
    identity_score = 1.0 if str(asset.external_id or "").strip() and (asset.checksum or asset.modified_at or asset.revision or payload_sha256) else 0.5
    provenance_score = 1.0 if contract.get("source_domain") and str(asset.external_id or "").strip() else 0.0
    score = (
        0.35 * schema_score
        + 0.25 * completeness_score
        + 0.20 * freshness_score
        + 0.10 * identity_score
        + 0.10 * provenance_score
    )
    if not validation.get("valid"):
        level = "LOW"
    elif score >= 0.85:
        level = "HIGH"
    elif score >= 0.65:
        level = "MEDIUM"
    else:
        level = "LOW"
    if expected and freshness_status == "UNKNOWN" and level == "HIGH":
        level = "MEDIUM"
    return {
        "score": round(score, 4),
        "level": level,
        "components": {
            "schema": round(schema_score, 4),
            "completeness": round(completeness_score, 4),
            "freshness": round(freshness_score, 4),
            "identity": round(identity_score, 4),
            "provenance": round(provenance_score, 4),
        },
        "freshness": {
            "status": freshness_status,
            "age_minutes": round(age_minutes, 1) if age_minutes is not None else None,
            "expected_minutes": expected,
        },
        "source": {
            "domain": contract.get("source_domain"),
            "contract_version": contract.get("version") or CONTRACT_VERSION,
            "source_modified_at": source_dt.isoformat() if source_dt else None,
        },
        "blocking": not validation.get("valid", False),
    }


def idempotency_key(system: ExternalSystem, asset: ExternalAsset, *, payload_sha256: str | None = None) -> str:
    fingerprint = asset.checksum or asset.modified_at or asset.revision or payload_sha256
    if not fingerprint:
        metadata_hash = hashlib.sha256(json.dumps(asset.metadata or {}, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
        fingerprint = metadata_hash
    raw = "|".join([
        system.id,
        system.contract_version or CONTRACT_VERSION,
        str(asset.external_id or ""),
        str(fingerprint),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


def age_quality_snapshot(quality: dict[str, Any], source_modified_at: datetime | None, expected_freshness_minutes: int | None, *, now: datetime | None = None) -> dict[str, Any]:
    """Recalculate only the time-dependent freshness component without inventing missing source facts."""
    now = now or utcnow()
    q = json.loads(json.dumps(quality or {}, default=str))
    components = dict(q.get("components") or {})
    expected = expected_freshness_minutes
    if source_modified_at is None:
        freshness_status = "UNKNOWN" if expected else ((q.get("freshness") or {}).get("status") or "NOT_CONFIGURED")
        freshness_score = 0.5 if expected else float(components.get("freshness", 1.0))
        age_minutes = None
    else:
        dt = source_modified_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_minutes = max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 60.0)
        if not expected:
            freshness_status, freshness_score = "OBSERVED", 1.0
        elif age_minutes <= expected:
            freshness_status, freshness_score = "FRESH", 1.0
        elif age_minutes <= expected * 2:
            freshness_status, freshness_score = "AGING", 0.7
        elif age_minutes <= expected * 4:
            freshness_status, freshness_score = "STALE", 0.4
        else:
            freshness_status, freshness_score = "STALE", 0.1
    components["freshness"] = round(freshness_score, 4)
    schema = float(components.get("schema", 0.0))
    completeness = float(components.get("completeness", 0.0))
    identity = float(components.get("identity", 0.0))
    provenance = float(components.get("provenance", 0.0))
    score = 0.35 * schema + 0.25 * completeness + 0.20 * freshness_score + 0.10 * identity + 0.10 * provenance
    blocking = bool(q.get("blocking")) or schema <= 0.0
    if blocking:
        level = "LOW"
    elif score >= 0.85:
        level = "HIGH"
    elif score >= 0.65:
        level = "MEDIUM"
    else:
        level = "LOW"
    if expected and freshness_status == "UNKNOWN" and level == "HIGH":
        level = "MEDIUM"
    q["score"] = round(score, 4)
    q["level"] = level
    q["components"] = components
    q["freshness"] = {
        "status": freshness_status,
        "age_minutes": round(age_minutes, 1) if age_minutes is not None else None,
        "expected_minutes": expected,
    }
    return q


def aggregate_system_quality(objects: list[ExternalObject], *, expected_freshness_minutes: int | None = None, quarantined: int = 0, failed: int = 0, now: datetime | None = None) -> dict[str, Any]:
    refreshed = [
        age_quality_snapshot(x.data_quality_json or {}, x.source_modified_at, expected_freshness_minutes, now=now)
        for x in objects if x.data_confidence_score is not None or x.data_quality_json
    ]
    if refreshed:
        avg = sum(float(q.get("score") or 0.0) for q in refreshed) / len(refreshed)
        freshness_counts: dict[str, int] = {}
        levels: dict[str, int] = {}
        for q in refreshed:
            status = (q.get("freshness") or {}).get("status") or "UNKNOWN"
            freshness_counts[status] = freshness_counts.get(status, 0) + 1
            level = q.get("level") or "UNKNOWN"
            levels[level] = levels.get(level, 0) + 1
    else:
        avg = 0.0
        freshness_counts = {}
        levels = {}
    if failed or quarantined:
        level = "LOW" if not refreshed or avg < 0.85 else "MEDIUM"
    elif not refreshed:
        level = "UNKNOWN"
    elif levels.get("LOW", 0):
        level = "LOW" if levels.get("LOW", 0) >= max(1, len(refreshed) // 4) else "MEDIUM"
    elif avg >= 0.85 and not levels.get("MEDIUM", 0):
        level = "HIGH"
    elif avg >= 0.65:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "score": round(avg, 4) if refreshed else None,
        "level": level,
        "object_count": len(objects),
        "scored_object_count": len(refreshed),
        "quarantined_count": int(quarantined),
        "failed_count": int(failed),
        "freshness_status_counts": freshness_counts,
        "confidence_level_counts": levels,
    }


def publish_integration_quality(system_code: str, quality: dict[str, Any]) -> None:
    score = quality.get("score")
    INTEGRATION_CONFIDENCE.labels(system=system_code).set(float(score) if score is not None else 0.0)
    INTEGRATION_QUARANTINE.labels(system=system_code).set(float(quality.get("quarantined_count") or 0))
