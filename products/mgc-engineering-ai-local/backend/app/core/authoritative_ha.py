from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prometheus_client import Gauge
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db.session import engine

AUTH_DB_PRIMARY = Gauge("mgc_authoritative_db_primary", "1 when the connected PostgreSQL node is a writable primary")
AUTH_EVIDENCE_ACTIVE = Gauge("mgc_authoritative_evidence_active", "1 when the evidence storage generation is active")
AUTH_WRITE_SAFE = Gauge("mgc_authoritative_write_safe", "1 when authoritative writes are permitted by DB/evidence HA fencing")
AUTH_EVIDENCE_GENERATION = Gauge("mgc_authoritative_evidence_generation", "Current authoritative evidence storage generation")

MARKER_SCHEMA = "mgc-evidence-ha-marker-v1"
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuthoritativeWriteFence(RuntimeError):
    """Raised when an authoritative mutation cannot be proven safe."""


@dataclass(frozen=True)
class DatabaseAuthority:
    enabled: bool
    supported: bool
    role: str
    writable: bool
    in_recovery: bool | None
    transaction_read_only: bool | None
    system_identifier: str | None
    expected_system_identifier_match: bool | None
    schema_version: str | None
    expected_schema_match: bool | None
    safe: bool
    detail: str

    def public(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "supported": self.supported,
            "role": self.role,
            "writable": self.writable,
            "in_recovery": self.in_recovery,
            "transaction_read_only": self.transaction_read_only,
            "system_identifier_present": bool(self.system_identifier),
            "expected_system_identifier_match": self.expected_system_identifier_match,
            "schema_version": self.schema_version,
            "expected_schema_match": self.expected_schema_match,
            "safe": self.safe,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class EvidenceAuthority:
    enabled: bool
    marker_present: bool
    cluster_id_match: bool | None
    state: str
    generation: int | None
    database_system_identifier_match: bool | None
    safe: bool
    detail: str

    def public(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "marker_present": self.marker_present,
            "cluster_id_match": self.cluster_id_match,
            "state": self.state,
            "generation": self.generation,
            "database_system_identifier_match": self.database_system_identifier_match,
            "safe": self.safe,
            "detail": self.detail,
        }


def _bool_setting(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _pg_system_identifier(conn: Connection) -> str | None:
    """Best-effort PostgreSQL cluster identity; lack of permission is not silently treated as a match."""
    try:
        value = conn.execute(text("SELECT system_identifier::text FROM pg_control_system()")) .scalar_one_or_none()
        return str(value) if value is not None else None
    except Exception:
        return None


def database_authority_probe(*, connection: Connection | None = None, bind: Engine | None = None) -> DatabaseAuthority:
    cfg = get_settings()
    enabled = bool(getattr(cfg, "database_ha_enabled", False))
    target_engine = bind or engine
    dialect = target_engine.dialect.name
    if not enabled:
        return DatabaseAuthority(False, dialect == "postgresql", "not_enforced", True, None, None, None, None, None, None, True, "database_ha_disabled")
    if dialect != "postgresql":
        return DatabaseAuthority(True, False, "unsupported", False, None, None, None, None, None, None, False, "database_ha_requires_postgresql")

    owns_connection = connection is None
    conn = connection or target_engine.connect()
    try:
        in_recovery = bool(conn.execute(text("SELECT pg_is_in_recovery()")) .scalar_one())
        raw_ro = str(conn.execute(text("SHOW transaction_read_only")) .scalar_one()).strip().lower()
        read_only = raw_ro in {"on", "true", "1", "yes"}
        role = "standby" if in_recovery else "primary"
        writable = (not in_recovery) and (not read_only)
        system_identifier = _pg_system_identifier(conn)
        expected = str(getattr(cfg, "database_ha_expected_system_identifier", "") or "").strip()
        identifier_match: bool | None = None
        if expected:
            identifier_match = bool(system_identifier and system_identifier == expected)

        try:
            schema_version_raw = conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one_or_none()
            schema_version = str(schema_version_raw) if schema_version_raw is not None else None
        except Exception:
            schema_version = None
        schema_match = schema_version == SCHEMA_VERSION if schema_version is not None else False

        safe = writable and (identifier_match is not False) and schema_match
        if expected and system_identifier is None:
            safe = False
            detail = "system_identifier_unavailable"
        elif identifier_match is False:
            detail = "unexpected_database_cluster"
        elif schema_version is None:
            detail = "database_schema_marker_unavailable"
        elif not schema_match:
            detail = "database_schema_marker_mismatch"
        elif not writable:
            detail = "connected_database_is_not_writable_primary"
        else:
            detail = "writable_primary_and_schema_confirmed"
        return DatabaseAuthority(True, True, role, writable, in_recovery, read_only, system_identifier, identifier_match, schema_version, schema_match, safe, detail)
    except Exception:
        return DatabaseAuthority(True, True, "unknown", False, None, None, None, None, None, None, False, "database_authority_probe_failed")
    finally:
        if owns_connection:
            conn.close()


def _marker_path(root: Path) -> Path:
    cfg = get_settings()
    rel = str(getattr(cfg, "evidence_ha_marker_relative_path", ".mgc-ha/STORAGE_EPOCH.json") or "").strip()
    rel_path = Path(rel)
    if not rel or rel_path.is_absolute():
        raise AuthoritativeWriteFence("evidence HA marker path must be relative to storage root")
    resolved_root = root.resolve()
    # Normalize '..' lexically without resolving symlinks; resolving first would erase
    # evidence that a marker or one of its parent directories is a symlink.
    candidate = Path(os.path.abspath(str(resolved_root / rel_path)))
    try:
        relative = candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise AuthoritativeWriteFence("evidence HA marker path escapes storage root") from exc
    current = resolved_root
    for part in relative.parts:
        current = current / part
        if current.exists() and current.is_symlink():
            raise AuthoritativeWriteFence("evidence HA marker path contains a symlink")
    return candidate


def read_evidence_marker(root: Path | None = None) -> dict[str, Any] | None:
    cfg = get_settings()
    storage_root = Path(root or cfg.storage_dir)
    path = _marker_path(storage_root)
    if path.is_symlink() or not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def evidence_authority_probe(*, database: DatabaseAuthority | None = None, root: Path | None = None) -> EvidenceAuthority:
    cfg = get_settings()
    enabled = bool(getattr(cfg, "evidence_ha_enabled", False))
    if not enabled:
        return EvidenceAuthority(False, False, None, "not_enforced", None, None, True, "evidence_ha_disabled")

    marker = read_evidence_marker(root)
    if not marker or marker.get("schema") != MARKER_SCHEMA:
        return EvidenceAuthority(True, False, None, "unknown", None, None, False, "evidence_ha_marker_missing_or_invalid")

    expected_cluster = str(getattr(cfg, "evidence_ha_cluster_id", "") or "").strip()
    marker_cluster = str(marker.get("cluster_id") or "").strip()
    cluster_match: bool | None = None
    if expected_cluster:
        cluster_match = marker_cluster == expected_cluster

    state = str(marker.get("state") or "unknown").strip().lower()
    try:
        generation = int(marker.get("generation"))
    except Exception:
        generation = None

    db = database or database_authority_probe()
    marker_db_id = str(marker.get("database_system_identifier") or "").strip()
    db_match: bool | None = None
    if marker_db_id:
        db_match = bool(db.system_identifier and db.system_identifier == marker_db_id)

    generation_ok = generation is not None and generation >= 1
    active = state == "active"
    safe = active and generation_ok and cluster_match is not False and db_match is not False
    if expected_cluster and not marker_cluster:
        safe = False
        detail = "evidence_cluster_id_missing"
    elif cluster_match is False:
        detail = "unexpected_evidence_cluster"
    elif not generation_ok:
        detail = "invalid_evidence_generation"
    elif state != "active":
        detail = "evidence_generation_not_active"
    elif marker_db_id and db.system_identifier is None:
        safe = False
        detail = "database_identity_unavailable_for_evidence_binding"
    elif db_match is False:
        detail = "evidence_database_identity_mismatch"
    else:
        detail = "active_evidence_generation_confirmed"
    return EvidenceAuthority(True, True, cluster_match, state, generation, db_match, safe, detail)


def authoritative_ha_snapshot(*, connection: Connection | None = None) -> dict[str, Any]:
    cfg = get_settings()
    db = database_authority_probe(connection=connection)
    evidence = evidence_authority_probe(database=db)
    enabled = bool(db.enabled or evidence.enabled)
    write_safe = bool(db.safe and evidence.safe)
    if not enabled:
        status = "DISABLED"
    elif write_safe:
        status = "HEALTHY"
    else:
        status = "UNSAFE"

    AUTH_DB_PRIMARY.set(1 if db.writable else 0)
    AUTH_EVIDENCE_ACTIVE.set(1 if evidence.safe else 0)
    AUTH_WRITE_SAFE.set(1 if write_safe else 0)
    AUTH_EVIDENCE_GENERATION.set(float(evidence.generation or 0))

    return {
        "application_version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "enabled": enabled,
        "status": status,
        "write_safe": write_safe,
        "database": db.public(),
        "evidence_storage": evidence.public(),
        "policy": {
            "postgresql_authoritative": True,
            "evidence_storage_authoritative": True,
            "database_primary_required_for_mutation": bool(getattr(cfg, "database_ha_require_primary_for_writes", True)),
            "evidence_active_generation_required_for_mutation": bool(getattr(cfg, "evidence_ha_require_active_for_writes", True)),
            "external_postgresql_ha_manager_required": True,
            "external_replication_or_shared_storage_required": True,
            "external_stonith_or_equivalent_fencing_required": True,
            "application_does_not_promote_postgresql": True,
            "application_does_not_claim_synchronous_storage_replication": True,
            "automatic_cross_schema_failover_authorized": False,
            "full_stack_ha_claimed": False,
            "production_authorized": False,
        },
    }


def assert_authoritative_write_safe(*, connection: Connection | None = None) -> dict[str, Any]:
    cfg = get_settings()
    if not bool(getattr(cfg, "authoritative_write_fence_enabled", True)):
        return {"enabled": False, "status": "BYPASSED", "write_safe": True}
    if not (bool(getattr(cfg, "database_ha_enabled", False)) or bool(getattr(cfg, "evidence_ha_enabled", False))):
        return {"enabled": False, "status": "DISABLED", "write_safe": True}
    snap = authoritative_ha_snapshot(connection=connection)
    if not snap.get("write_safe"):
        raise AuthoritativeWriteFence("authoritative write fence is closed")
    return snap


def should_fence_http_method(method: str) -> bool:
    return str(method or "").upper() in MUTATING_METHODS
