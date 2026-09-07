from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuditEvent

_PLACEHOLDER_RE = re.compile(r"(?:change-me|replace-me|replace-with|local-only|^mgc$)", re.I)
_SENSITIVE_KEY_RE = re.compile(r"(?:password|secret|token|api[_-]?key|private[_-]?key|credential)", re.I)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def redact_details(value):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if _SENSITIVE_KEY_RE.search(str(k)) else redact_details(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_details(v) for v in value]
    return value


def security_posture() -> dict:
    cfg = get_settings()
    prod = cfg.app_env.lower() in {"prod", "production"}
    checks: list[dict] = []

    def add(code: str, ok: bool, severity: str, detail: str):
        checks.append({"code": code, "ok": bool(ok), "severity": severity, "detail": detail})

    add("auth.engineer_only", cfg.engineer_only_access, "critical", "Engineer-only access must remain enabled")
    add("auth.no_api_key_prod", not (prod and cfg.allow_api_key_auth_in_prod), "critical", "Shared API-key human auth must be disabled in production")
    add("auth.mode", (not prod) or cfg.auth_mode == "oidc", "critical", "Production human access should use OIDC")
    if prod:
        issuer = urlparse(cfg.oidc_issuer or "")
        jwks = urlparse(cfg.oidc_jwks_url or "") if cfg.oidc_jwks_url else None
        add("oidc.issuer_https", cfg.allow_insecure_oidc_in_prod or issuer.scheme == "https", "critical", "OIDC issuer must use HTTPS")
        add("oidc.audience", bool(cfg.oidc_audience), "critical", "OIDC audience must be configured")
        add("oidc.jwks_https", cfg.allow_insecure_oidc_in_prod or not jwks or jwks.scheme == "https", "high", "Explicit JWKS URL must use HTTPS")
    algs = cfg.oidc_allowed_algorithm_set
    add("oidc.alg_allowlist", bool(algs) and all(a.upper() != "NONE" and not a.upper().startswith("HS") for a in algs), "critical", "Only asymmetric OIDC signature algorithms are allowed")
    add("oidc.clock_skew", 0 <= int(cfg.oidc_clock_skew_seconds) <= 300, "medium", "OIDC clock skew must be bounded to 300 seconds")
    add("trusted_headers.fail_closed", not (prod and cfg.allow_trusted_headers_in_prod and not cfg.trusted_proxy_secret), "critical", "Production trusted headers require a proxy secret")
    add("cors.explicit", "*" not in cfg.cors_list, "high", "Wildcard CORS is not allowed")
    add("audit.retention", int(cfg.audit_retention_days) >= int(cfg.audit_min_retention_days), "high", "Configured audit retention must meet minimum policy")
    add("tls.edge_policy", not prod or cfg.security_require_tls_edge, "high", "Enterprise deployment requires TLS at the edge")

    secret_values = {
        "API_KEY": cfg.api_key,
        "NEO4J_PASSWORD": cfg.neo4j_password,
        "MINIO_SECRET_KEY": cfg.minio_secret_key,
    }
    for name, value in secret_values.items():
        if prod:
            add(f"secret.{name.lower()}", bool(value) and not _PLACEHOLDER_RE.search(str(value)), "critical", f"{name} must not use a placeholder value")

    failed = [c for c in checks if not c["ok"]]
    critical = [c for c in failed if c["severity"] == "critical"]
    return {
        "status": "FAIL" if critical else ("WARN" if failed else "PASS"),
        "production": prod,
        "checks": checks,
        "failed_count": len(failed),
        "critical_failed_count": len(critical),
        "human_go_live_required": True,
    }


def build_audit_export(db: Session, *, since: datetime | None = None, until: datetime | None = None, limit: int | None = None) -> tuple[bytes, dict]:
    cfg = get_settings()
    cap = max(1, min(int(limit or cfg.audit_export_max_rows), int(cfg.audit_export_max_rows)))
    stmt = select(AuditEvent)
    if since:
        stmt = stmt.where(AuditEvent.created_at >= _utc(since))
    if until:
        stmt = stmt.where(AuditEvent.created_at <= _utc(until))
    rows = db.scalars(stmt.order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).limit(cap)).all()
    chain = ""
    lines: list[bytes] = []
    for row in rows:
        obj = {
            "id": row.id,
            "user": row.user,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": redact_details(row.details or {}),
            "created_at": _utc(row.created_at).isoformat() if row.created_at else None,
            "previous_export_hash": chain,
        }
        canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        chain = hashlib.sha256((chain.encode("ascii") + canonical)).hexdigest()
        obj["export_hash"] = chain
        lines.append(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8") + b"\n")
    payload = b"".join(lines)
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {
        "schema": "mgc-audit-export-v1",
        "row_count": len(rows),
        "sha256": digest,
        "chain_head": chain,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "redacted": True,
        "truncated": len(rows) >= cap,
        "max_rows": cap,
    }
    return payload, manifest


def audit_retention_preview(db: Session, *, now: datetime | None = None) -> dict:
    cfg = get_settings()
    current = _utc(now) or datetime.now(timezone.utc)
    retention_days = max(int(cfg.audit_retention_days), int(cfg.audit_min_retention_days))
    cutoff = current - timedelta(days=retention_days)
    count = int(db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.created_at < cutoff)) or 0)
    return {
        "retention_days": retention_days,
        "minimum_retention_days": int(cfg.audit_min_retention_days),
        "cutoff": cutoff.isoformat(),
        "eligible_rows": count,
        "destructive": count > 0,
    }


def apply_audit_retention(db: Session, *, confirm: str, actor: str, now: datetime | None = None) -> dict:
    if confirm != "PURGE_AUDIT":
        raise ValueError("Explicit confirmation PURGE_AUDIT is required")
    preview = audit_retention_preview(db, now=now)
    cutoff = datetime.fromisoformat(preview["cutoff"])
    deleted = db.execute(delete(AuditEvent).where(AuditEvent.created_at < cutoff)).rowcount or 0
    db.commit()
    # Record the governance action after the purge so the action itself is retained.
    row = AuditEvent(
        user=actor,
        action="AUDIT_RETENTION_APPLIED",
        entity_type="audit",
        details={"deleted_rows": int(deleted), "cutoff": preview["cutoff"], "retention_days": preview["retention_days"]},
    )
    db.add(row)
    db.commit()
    return {**preview, "deleted_rows": int(deleted), "applied": True}
