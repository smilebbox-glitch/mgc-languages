from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import select, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class RLSIdentity:
    user_id: str
    role: str
    department: str


@dataclass(frozen=True)
class GovernanceCoreBindings:
    apply_rls_context: Callable[..., None]
    audit_event: Callable[..., None]
    verify_audit_chain: Callable[[Session], dict[str, Any]]


def rls_identity(user: Any | None = None, *, system_admin: bool = False) -> RLSIdentity:
    """Return the exact transaction-local identity used by PostgreSQL FORCE RLS."""
    return RLSIdentity(
        user_id=str(user.id) if user else "0",
        role="admin" if system_admin else (str(user.role) if user else ""),
        department=str(user.department) if user else "__system__",
    )


def canonical_metadata(metadata: dict[str, Any] | None = None) -> str:
    """Stable JSON representation used by the historical audit hash chain."""
    return json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True, default=str)


def audit_event_hash(
    previous_hash: str,
    event_type: str,
    actor_user_id: int | None,
    target_type: str,
    target_id: str,
    request_id: str,
    source_ip_hash: str,
    metadata_json: str,
) -> str:
    canonical = "|".join(
        [
            previous_hash,
            event_type,
            str(actor_user_id or ""),
            target_type,
            target_id,
            request_id,
            source_ip_hash,
            metadata_json,
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_governance_core(
    *,
    audit_log_model: Any,
    audit_anchor_model: Any,
    database_url: str,
    rls_enabled: bool,
    audit_chain_lock_id: int,
    client_key: Callable[[Any], str],
) -> GovernanceCoreBindings:
    """Build model-aware RLS/audit functions without importing the legacy app module."""

    def apply_rls_context(
        db: Session,
        user: Any | None = None,
        *,
        system_admin: bool = False,
    ) -> None:
        if not rls_enabled or not database_url.startswith("postgresql"):
            return
        identity = rls_identity(user, system_admin=system_admin)
        db.execute(text("SELECT set_config('app.user_id', :v, true)"), {"v": identity.user_id})
        db.execute(text("SELECT set_config('app.role', :v, true)"), {"v": identity.role})
        db.execute(text("SELECT set_config('app.department', :v, true)"), {"v": identity.department})

    apply_rls_context.__name__ = "apply_rls_context"
    apply_rls_context.__qualname__ = "apply_rls_context"

    def audit_event(
        db: Session,
        event_type: str,
        *,
        actor_user_id: int | None = None,
        target_type: str = "",
        target_id: str = "",
        request: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        metadata_json = canonical_metadata(metadata)
        if database_url.startswith("postgresql"):
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": audit_chain_lock_id},
            )
        previous = db.scalar(select(audit_log_model).order_by(audit_log_model.id.desc()).limit(1))
        if previous is None:
            anchor = db.get(audit_anchor_model, 1)
            previous_hash = anchor.last_deleted_hash if anchor else ""
        else:
            previous_hash = previous.event_hash or ""
        request_id = getattr(getattr(request, "state", None), "request_id", "") if request else ""
        source_ip_hash = client_key(request) if request else ""
        event_hash = audit_event_hash(
            previous_hash,
            event_type,
            actor_user_id,
            target_type,
            target_id,
            request_id,
            source_ip_hash,
            metadata_json,
        )
        db.add(
            audit_log_model(
                event_type=event_type,
                actor_user_id=actor_user_id,
                target_type=target_type,
                target_id=target_id,
                request_id=request_id,
                source_ip_hash=source_ip_hash,
                metadata_json=metadata_json,
                previous_hash=previous_hash,
                event_hash=event_hash,
            )
        )

    audit_event.__name__ = "audit_event"
    audit_event.__qualname__ = "audit_event"

    def verify_audit_chain(db: Session) -> dict[str, Any]:
        rows = db.scalars(select(audit_log_model).order_by(audit_log_model.id.asc())).all()
        anchor = db.get(audit_anchor_model, 1)
        previous = anchor.last_deleted_hash if anchor else ""
        broken: list[int] = []
        for row in rows:
            expected = audit_event_hash(
                previous,
                row.event_type,
                row.actor_user_id,
                row.target_type,
                row.target_id,
                row.request_id,
                row.source_ip_hash,
                row.metadata_json,
            )
            if (row.previous_hash or "") != previous or (row.event_hash or "") != expected:
                broken.append(int(row.id))
            previous = row.event_hash or expected
        return {
            "ok": not broken,
            "events": len(rows),
            "broken_ids": broken[:50],
            "algorithm": "sha256 hash chain",
        }

    verify_audit_chain.__name__ = "verify_audit_chain"
    verify_audit_chain.__qualname__ = "verify_audit_chain"

    return GovernanceCoreBindings(
        apply_rls_context=apply_rls_context,
        audit_event=audit_event,
        verify_audit_chain=verify_audit_chain,
    )


__all__ = [
    "RLSIdentity",
    "GovernanceCoreBindings",
    "rls_identity",
    "canonical_metadata",
    "audit_event_hash",
    "build_governance_core",
]
