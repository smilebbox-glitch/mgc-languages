from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ExternalObject, ExternalSystem, IntegrationIngestEvent, IntegrationRun
from app.integrations.base import ExternalAsset
from app.integrations.registry import build_connector
from app.services.integration_hardening import asset_snapshot, contract_for, idempotency_key, validate_asset_contract

CERTIFICATION_SCHEMA = "mgc.integration-certification.v1"
CERTIFIED_DOMAINS = ("plm", "pdm", "erp", "mes", "qms")

DOMAIN_PROFILES: dict[str, dict[str, Any]] = {
    "plm": {
        "purpose": "engineering product lifecycle master",
        "connector_types": ["plm_rest", "engineering_rest"],
        "required_capabilities": ["stable_external_id", "revision_or_timestamp", "deterministic_pull", "idempotent_replay", "cached_read_only"],
        "recommended_required_fields": ["external_id", "name", "kind", "revision", "modified_at"],
        "recommended_reconciliation_role": "ebom",
    },
    "pdm": {
        "purpose": "engineering document/product data master",
        "connector_types": ["pdm_rest", "engineering_rest"],
        "required_capabilities": ["stable_external_id", "revision_or_timestamp", "deterministic_pull", "idempotent_replay", "cached_read_only"],
        "recommended_required_fields": ["external_id", "name", "kind", "revision", "modified_at"],
        "recommended_reconciliation_role": "ebom",
    },
    "erp": {
        "purpose": "enterprise material/supplier master",
        "connector_types": ["erp_rest", "engineering_rest"],
        "required_capabilities": ["stable_external_id", "source_timestamp", "deterministic_pull", "idempotent_replay", "cached_read_only"],
        "recommended_required_fields": ["external_id", "name", "kind", "part_number", "modified_at"],
        "recommended_reconciliation_role": "mbom",
    },
    "mes": {
        "purpose": "manufacturing execution/genealogy source",
        "connector_types": ["mes_rest", "engineering_rest"],
        "required_capabilities": ["stable_external_id", "source_timestamp", "deterministic_pull", "idempotent_replay", "cached_read_only"],
        "recommended_required_fields": ["external_id", "name", "kind", "modified_at"],
        "recommended_reconciliation_role": "genealogy",
    },
    "qms": {
        "purpose": "quality/defect source",
        "connector_types": ["qms_rest", "engineering_rest"],
        "required_capabilities": ["stable_external_id", "source_timestamp", "deterministic_pull", "idempotent_replay", "cached_read_only"],
        "recommended_required_fields": ["external_id", "name", "kind", "modified_at"],
        "recommended_reconciliation_role": "defects",
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _check(code: str, status: str, actual: Any = None, expected: Any = None, *, critical: bool = True) -> dict[str, Any]:
    return {"code": code, "status": status, "critical": critical, "actual": actual, "expected": expected}


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_domain(system: ExternalSystem) -> str:
    domain = str(system.source_domain or "").strip().lower()
    if domain in CERTIFIED_DOMAINS:
        return domain
    prefix = str(system.connector_type or "").split("_", 1)[0].lower()
    return prefix if prefix in CERTIFIED_DOMAINS else domain


def _policy(system: ExternalSystem) -> dict[str, Any]:
    cfg = system.config_json or {}
    raw = cfg.get("certification") if isinstance(cfg.get("certification"), dict) else {}
    return {
        "declared_capabilities": sorted({str(x).strip() for x in (raw.get("declared_capabilities") or []) if str(x).strip()}),
        "checkpoint_mode": str(raw.get("checkpoint_mode") or "fingerprint").strip().lower(),
        "degraded_mode": str(raw.get("degraded_mode") or "cached_read_only").strip().lower(),
        "writeback_enabled": bool(raw.get("writeback_enabled", False)),
        "allow_local_http": bool(raw.get("allow_local_http", False)),
        "enforce_for_sync": bool(raw.get("enforce_for_sync", False)),
        # Backward-compatible opt-in: existing v6.3.28 configs remain fail-closed.
        "recovery_sync_enabled": bool(raw.get("recovery_sync_enabled", False)),
        "min_sync_success_rate": float(raw.get("min_sync_success_rate", 0.95) or 0.95),
        "max_quarantine_ratio": float(raw.get("max_quarantine_ratio", 0.02) or 0.02),
        # Bound degraded cached reads without introducing a new DB column. By default
        # the cache may be at most 2x the source freshness target, with a 60-minute floor.
        "max_cache_staleness_minutes": float(
            raw.get("max_cache_staleness_minutes")
            if raw.get("max_cache_staleness_minutes") is not None
            else max(float(system.expected_freshness_minutes or 60) * 2.0, 60.0)
        ),
    }


def static_contract_report(system: ExternalSystem) -> dict[str, Any]:
    domain = _source_domain(system)
    profile = DOMAIN_PROFILES.get(domain)
    policy = _policy(system)
    cfg = system.config_json or {}
    checks: list[dict[str, Any]] = []

    checks.append(_check("SUPPORTED_DOMAIN", "PASS" if profile else "FAIL", domain, list(CERTIFIED_DOMAINS)))
    if profile:
        checks.append(_check("CONNECTOR_TYPE", "PASS" if system.connector_type in profile["connector_types"] else "FAIL", system.connector_type, profile["connector_types"]))
    checks.append(_check("CONTRACT_VERSION", "PASS" if system.contract_version == "mgc-integration-v1" else "FAIL", system.contract_version, "mgc-integration-v1"))

    secret_refs = system.secret_config_json or {}
    refs_ok = all(str(k).endswith("_env") and isinstance(v, str) and bool(v.strip()) for k, v in secret_refs.items())
    checks.append(_check("SECRET_REFERENCES_ONLY", "PASS" if refs_ok else "FAIL", sorted(secret_refs), "*_env references"))

    forbidden = {"token", "api_key", "password", "client_secret", "private_key"}
    raw_secret_keys = sorted(k for k, v in cfg.items() if k in forbidden and v not in (None, "", False))
    checks.append(_check("NO_RAW_SECRETS_IN_CONFIG", "PASS" if not raw_secret_keys else "FAIL", raw_secret_keys, []))

    base_url = str(cfg.get("base_url") or "")
    if system.connector_type.endswith("_rest") or system.connector_type == "engineering_rest":
        parsed = urlparse(base_url)
        local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "integration-simulator"}
        secure_transport = parsed.scheme == "https" or (policy["allow_local_http"] and local_http)
        checks.append(_check("TLS_OR_EXPLICIT_LOCAL_SIMULATOR", "PASS" if secure_transport else "FAIL", parsed.scheme or None, "https"))

    if profile:
        declared = set(policy["declared_capabilities"])
        missing_caps = [x for x in profile["required_capabilities"] if x not in declared]
        checks.append(_check("CAPABILITY_DECLARATION", "PASS" if not missing_caps else "CONDITIONAL", missing_caps, profile["required_capabilities"], critical=False))
        required_fields = set(contract_for(system).get("required_fields") or [])
        recommended = set(profile["recommended_required_fields"])
        missing_fields = sorted(recommended - required_fields)
        checks.append(_check("DOMAIN_REQUIRED_FIELDS", "PASS" if not missing_fields else "CONDITIONAL", missing_fields, sorted(recommended), critical=False))

    checks.append(_check("WRITEBACK_DISABLED", "PASS" if not policy["writeback_enabled"] else "FAIL", policy["writeback_enabled"], False))
    checks.append(_check("DEGRADED_MODE", "PASS" if policy["degraded_mode"] == "cached_read_only" else "FAIL", policy["degraded_mode"], "cached_read_only"))
    checks.append(_check(
        "BOUNDED_CACHE_STALENESS",
        "PASS" if 0 < policy["max_cache_staleness_minutes"] <= 10080 else "FAIL",
        policy["max_cache_staleness_minutes"],
        "0 < minutes <= 10080",
    ))
    checks.append(_check("CHECKPOINT_MODE", "PASS" if policy["checkpoint_mode"] in {"source_checkpoint", "fingerprint"} else "FAIL", policy["checkpoint_mode"], ["source_checkpoint", "fingerprint"]))

    critical_fail = any(x["critical"] and x["status"] == "FAIL" for x in checks)
    conditional = any(x["status"] == "CONDITIONAL" for x in checks)
    decision = "NO_GO" if critical_fail else ("CONDITIONAL" if conditional else "PASS")
    return {
        "schema": CERTIFICATION_SCHEMA,
        "scope": "static_contract",
        "domain": domain,
        "profile": profile,
        "policy": policy,
        "decision": decision,
        "checks": checks,
        "production_authorized": False,
    }


def _safe_asset_view(asset: ExternalAsset) -> dict[str, Any]:
    snap = asset_snapshot(asset)
    # Metadata can contain vendor fields; the report only needs a canonical digest.
    return {
        "external_id_sha256": hashlib.sha256(str(asset.external_id).encode()).hexdigest(),
        "kind": asset.kind,
        "has_revision": bool(asset.revision),
        "has_modified_at": bool(asset.modified_at),
        "has_checksum": bool(asset.checksum),
        "snapshot_sha256": _canonical_hash(snap),
    }


def live_contract_probe(system: ExternalSystem, *, sample_limit: int = 20) -> dict[str, Any]:
    sample_limit = min(max(int(sample_limit), 1), 50)
    static = static_contract_report(system)
    checks = list(static["checks"])
    if static["decision"] == "NO_GO":
        return {**static, "scope": "live_probe", "decision": "NO_GO", "sample_count": 0, "samples": []}

    connector = build_connector(system.connector_type, system.config_json or {}, system.secret_config_json or {})
    health = connector.health()
    checks.append(_check("LIVE_HEALTH", "PASS" if health.ok else "FAIL", "ok" if health.ok else "failed", "ok"))
    if not health.ok:
        return {**static, "scope": "live_probe", "decision": "NO_GO", "checks": checks, "sample_count": 0, "samples": [], "health_latency_ms": health.latency_ms}

    try:
        page_a = connector.list_assets(cursor=None, limit=sample_limit)
        page_b = connector.list_assets(cursor=None, limit=sample_limit)
    except Exception:
        checks.append(_check("READ_ONLY_LIST_PROBE", "FAIL", "error", "two deterministic reads"))
        return {**static, "scope": "live_probe", "decision": "NO_GO", "checks": checks, "sample_count": 0, "samples": [], "health_latency_ms": health.latency_ms}

    snaps_a = [asset_snapshot(x) for x in page_a.assets]
    snaps_b = [asset_snapshot(x) for x in page_b.assets]
    deterministic = _canonical_hash(snaps_a) == _canonical_hash(snaps_b)
    checks.append(_check("DETERMINISTIC_FIRST_PAGE", "PASS" if deterministic else "FAIL", deterministic, True))

    ids = [str(x.external_id or "") for x in page_a.assets]
    stable_unique_ids = bool(ids) and len(ids) == len(set(ids)) and all(ids)
    checks.append(_check("STABLE_UNIQUE_EXTERNAL_IDS", "PASS" if stable_unique_ids else ("CONDITIONAL" if not ids else "FAIL"), len(set(ids)), len(ids), critical=bool(ids)))

    validations = [validate_asset_contract(x, contract_for(system)) for x in page_a.assets]
    valid_count = sum(1 for x in validations if x.get("valid"))
    checks.append(_check("SAMPLE_CONTRACT_VALIDATION", "PASS" if valid_count == len(validations) and validations else ("CONDITIONAL" if not validations else "FAIL"), valid_count, len(validations), critical=bool(validations)))

    keys_a = [idempotency_key(system, x) for x in page_a.assets]
    keys_b = [idempotency_key(system, x) for x in page_b.assets]
    replay_safe = keys_a == keys_b and len(keys_a) == len(set(keys_a))
    checks.append(_check("IDEMPOTENT_REPLAY_KEYS", "PASS" if replay_safe and keys_a else ("CONDITIONAL" if not keys_a else "FAIL"), replay_safe, True, critical=bool(keys_a)))

    checkpoint_mode = static["policy"]["checkpoint_mode"]
    if checkpoint_mode == "source_checkpoint":
        cp_ok = bool(page_a.checkpoint) and page_a.checkpoint == page_b.checkpoint
        checks.append(_check("SOURCE_CHECKPOINT", "PASS" if cp_ok else "FAIL", page_a.checkpoint, "stable non-empty checkpoint"))
    else:
        fp = _canonical_hash({"assets": snaps_a, "next_cursor": page_a.next_cursor})
        checks.append(_check("FINGERPRINT_CHECKPOINT", "PASS", fp, "sha256"))

    critical_fail = any(x["critical"] and x["status"] == "FAIL" for x in checks)
    conditional = any(x["status"] == "CONDITIONAL" for x in checks)
    decision = "NO_GO" if critical_fail else ("CONDITIONAL" if conditional else "PASS")
    return {
        **static,
        "scope": "live_probe",
        "decision": decision,
        "checks": checks,
        "sample_count": len(page_a.assets),
        "samples": [_safe_asset_view(x) for x in page_a.assets],
        "health_latency_ms": health.latency_ms,
        "page_fingerprint_sha256": _canonical_hash(snaps_a),
        "production_authorized": False,
    }


def _age_minutes(value: datetime | None, now: datetime) -> float | None:
    if value is None:
        return None
    # SQLite commonly round-trips DateTime without tzinfo. Persisted integration
    # timestamps are UTC, so normalize naive values instead of mixing aware/naive.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max((now.astimezone(timezone.utc) - value.astimezone(timezone.utc)).total_seconds() / 60.0, 0.0)


def runtime_posture(db: Session, system: ExternalSystem, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or _utcnow()
    static = static_contract_report(system)
    total_objects = int(db.scalar(select(func.count()).select_from(ExternalObject).where(ExternalObject.system_id == system.id)) or 0)
    latest_cached_at = db.scalar(
        select(ExternalObject.last_seen_at)
        .where(ExternalObject.system_id == system.id)
        .order_by(ExternalObject.last_seen_at.desc())
        .limit(1)
    )
    quarantined = int(db.scalar(select(func.count()).select_from(IntegrationIngestEvent).where(IntegrationIngestEvent.system_id == system.id, IntegrationIngestEvent.status == "quarantined")) or 0)
    recent_runs = db.scalars(select(IntegrationRun).where(IntegrationRun.system_id == system.id).order_by(IntegrationRun.started_at.desc()).limit(20)).all()
    completed = [x for x in recent_runs if x.status in {"ok", "completed", "failed", "partial", "success"}]
    succeeded = [x for x in completed if x.status in {"ok", "completed", "success"} and not x.failed_count]
    success_rate = len(succeeded) / len(completed) if completed else None
    quarantine_ratio = quarantined / max(total_objects + quarantined, 1)
    policy = static["policy"]
    cache_age_minutes = _age_minutes(latest_cached_at, now)
    cache_stale = bool(total_objects) and (
        cache_age_minutes is None or cache_age_minutes > policy["max_cache_staleness_minutes"]
    )

    reasons: list[str] = []
    mode = "ACTIVE"
    if not system.enabled:
        mode, reasons = "BLOCKED", ["INTEGRATION_DISABLED"]
    elif static["decision"] == "NO_GO":
        mode, reasons = "BLOCKED", ["STATIC_CONTRACT_NO_GO"]
    elif system.last_health_status == "failed":
        reasons = ["SOURCE_HEALTH_FAILED"]
        if not total_objects:
            mode = "BLOCKED"
            reasons.append("NO_CACHED_ENGINEERING_DATA")
        elif cache_stale:
            mode = "BLOCKED"
            reasons.append("CACHE_STALE")
        else:
            mode = "DEGRADED_READ_ONLY"
    elif cache_stale:
        mode, reasons = "DEGRADED_READ_ONLY", ["CACHE_STALE"]
    elif quarantine_ratio > policy["max_quarantine_ratio"]:
        mode, reasons = "DEGRADED_READ_ONLY", ["QUARANTINE_RATIO_EXCEEDED"]
    elif success_rate is not None and success_rate < policy["min_sync_success_rate"]:
        mode, reasons = "DEGRADED_READ_ONLY", ["SYNC_SUCCESS_RATE_LOW"]
    elif static["decision"] == "CONDITIONAL":
        mode, reasons = "DEGRADED_READ_ONLY", ["CERTIFICATION_INCOMPLETE"]

    recovery_reasons = {"SOURCE_HEALTH_FAILED", "CACHE_STALE", "NO_CACHED_ENGINEERING_DATA"}
    recovery_sync_allowed = (
        bool(reasons)
        and policy["recovery_sync_enabled"]
        and system.enabled
        and static["decision"] != "NO_GO"
        and set(reasons).issubset(recovery_reasons)
    )

    return {
        "schema": "mgc.integration-runtime-posture.v2",
        "system_id": system.id,
        "system_code": system.code,
        "domain": _source_domain(system),
        "mode": mode,
        "reasons": reasons,
        "cached_objects": total_objects,
        "latest_cached_at": latest_cached_at.isoformat() if latest_cached_at else None,
        "cache_age_minutes": round(cache_age_minutes, 3) if cache_age_minutes is not None else None,
        "max_cache_staleness_minutes": policy["max_cache_staleness_minutes"],
        "cache_stale": cache_stale,
        "quarantined": quarantined,
        "quarantine_ratio": round(quarantine_ratio, 6),
        "recent_sync_success_rate": round(success_rate, 6) if success_rate is not None else None,
        "static_certification": static["decision"],
        "authoritative_source_mutation_allowed": False,
        "cached_engineering_reads_allowed": mode in {"ACTIVE", "DEGRADED_READ_ONLY"} and not cache_stale,
        "recovery_sync_allowed": recovery_sync_allowed,
    }


def sync_allowed(db: Session, system: ExternalSystem) -> tuple[bool, dict[str, Any]]:
    policy = _policy(system)
    posture = runtime_posture(db, system)
    if not policy["enforce_for_sync"]:
        return True, posture
    # Fail closed for quality/certification degradation, but permit a bounded
    # source pull when the only problem is source health/cache freshness.
    return posture["mode"] == "ACTIVE" or posture["recovery_sync_allowed"], posture
