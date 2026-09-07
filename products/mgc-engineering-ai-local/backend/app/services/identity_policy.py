from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import Identity, authentication_age_seconds, identity_snapshot, is_engineering_admin
from app.db.models import EngineeringIdentityDelegation, EngineeringIdentityPolicy

KNOWN_ACTIONS = {
    "approval_submit", "approval_decision", "approval_policy_admin", "identity_policy_admin",
    "delegation_admin", "release_package_create", "release_package_submit", "release_package_release",
    "handover_target_admin", "handover_create", "handover_authorize", "handover_execute", "handover_reconcile",
    "retention_policy_admin", "legal_hold_admin", "lifecycle_archive", "purge_create", "purge_authorize", "purge_execute",
}

PRIVILEGED_ACTIONS = {
    "approval_decision",
    "approval_policy_admin",
    "identity_policy_admin",
    "delegation_admin",
    "release_package_release",
    "handover_target_admin", "handover_authorize", "handover_execute",
    "retention_policy_admin", "legal_hold_admin", "purge_authorize", "purge_execute",
}
HUMAN_ONLY_ACTIONS = {
    "approval_decision",
    "approval_policy_admin",
    "identity_policy_admin",
    "delegation_admin",
    "release_package_release",
    "handover_target_admin", "handover_create", "handover_authorize", "handover_execute",
    "retention_policy_admin", "legal_hold_admin", "purge_create", "purge_authorize", "purge_execute",
}
DELEGATABLE_ACTIONS = {"approval_decision"}


@dataclass
class PolicyDecision:
    allowed: bool
    action: str
    policy_id: str | None
    effective_groups: list[str]
    delegation_ids: list[str]
    reason: str
    identity: dict
    assurance: dict


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _specificity(policy: EngineeringIdentityPolicy) -> int:
    return (4 if policy.project_code else 0) + (2 if policy.manufacturing_area else 0) + (1 if policy.entity_type else 0)


def resolve_identity_policy(
    db: Session,
    *,
    action: str,
    project_code: str | None,
    manufacturing_area: str | None,
    entity_type: str | None,
) -> EngineeringIdentityPolicy | None:
    rows = db.scalars(
        select(EngineeringIdentityPolicy).where(
            EngineeringIdentityPolicy.action == action,
            EngineeringIdentityPolicy.active == True,
        ).order_by(EngineeringIdentityPolicy.created_at.desc())
    ).all()
    matches: list[EngineeringIdentityPolicy] = []
    for p in rows:
        if p.project_code and p.project_code != project_code:
            continue
        if p.manufacturing_area and p.manufacturing_area != manufacturing_area:
            continue
        if p.entity_type and p.entity_type != entity_type:
            continue
        matches.append(p)
    matches.sort(key=_specificity, reverse=True)
    return matches[0] if matches else None


def _active_delegations(
    db: Session,
    identity: Identity,
    *,
    action: str,
    project_code: str | None,
    manufacturing_area: str | None,
    entity_type: str | None,
) -> list[EngineeringIdentityDelegation]:
    if action not in DELEGATABLE_ACTIONS:
        return []
    now = _now()
    rows = db.scalars(
        select(EngineeringIdentityDelegation).where(
            EngineeringIdentityDelegation.delegate == identity.user,
            EngineeringIdentityDelegation.revoked_at.is_(None),
            EngineeringIdentityDelegation.valid_from <= now,
            EngineeringIdentityDelegation.valid_until >= now,
        )
    ).all()
    out = []
    for d in rows:
        if action not in (d.actions_json or []):
            continue
        if d.project_code and d.project_code != project_code:
            continue
        if d.manufacturing_area and d.manufacturing_area != manufacturing_area:
            continue
        if d.entity_type and d.entity_type != entity_type:
            continue
        out.append(d)
    return out


def _assurance_payload(identity: Identity, *, max_age: int | None, required_acr: list[str]) -> dict:
    return {
        "auth_mode": identity.auth_mode,
        "acr": identity.acr,
        "auth_age_seconds": authentication_age_seconds(identity),
        "max_auth_age_seconds": max_age,
        "required_acr_values": sorted(set(required_acr)),
        "service_account": bool(identity.is_service_account),
    }


def enforce_identity_policy(
    db: Session,
    identity: Identity,
    *,
    action: str,
    project_code: str | None = None,
    manufacturing_area: str | None = None,
    entity_type: str | None = None,
    allow_delegation: bool = False,
) -> PolicyDecision:
    cfg = get_settings()
    base_groups = {g for g in identity.groups if g != "all"}
    policy = resolve_identity_policy(
        db,
        action=action,
        project_code=project_code,
        manufacturing_area=manufacturing_area,
        entity_type=entity_type,
    ) if cfg.identity_policy_enforcement_enabled else None

    if identity.is_service_account and action in HUMAN_ONLY_ACTIONS:
        raise PermissionError("Human identity required for this privileged engineering action")

    delegations: list[EngineeringIdentityDelegation] = []
    effective_groups = set(base_groups)
    policy_allows_delegation = bool(policy.delegation_allowed) if policy else False
    if allow_delegation and policy_allows_delegation:
        delegations = _active_delegations(
            db, identity, action=action, project_code=project_code,
            manufacturing_area=manufacturing_area, entity_type=entity_type,
        )
        for d in delegations:
            # Delegation may never mint Engineering Admin authority.
            delegated = set(d.delegated_groups_json or []) - get_settings().engineering_admin_group_set
            effective_groups |= delegated

    require_oidc = bool(policy.require_oidc) if policy else False
    max_age = policy.max_auth_age_seconds if policy else None
    required_acr = list(policy.required_acr_values_json or []) if policy else []

    if action in PRIVILEGED_ACTIONS and cfg.app_env.lower() in {"prod", "production"}:
        if cfg.privileged_actions_require_oidc_in_prod:
            require_oidc = True
        if max_age is None:
            max_age = max(60, int(cfg.privileged_reauth_max_age_seconds))
        if not required_acr:
            required_acr = sorted(cfg.privileged_required_acr_set)

    if require_oidc and identity.auth_mode != "oidc":
        raise PermissionError("Corporate OIDC identity is required for this action")
    if max_age is not None:
        age = authentication_age_seconds(identity)
        if age is None:
            raise PermissionError("Fresh authentication evidence is required for this action")
        if age > int(max_age):
            raise PermissionError("Authentication is too old for this privileged action; re-authentication is required")
    if required_acr and identity.acr not in set(required_acr):
        raise PermissionError("Authentication assurance level does not satisfy the identity policy")

    if policy:
        denied = set(policy.denied_groups_json or [])
        if denied & effective_groups:
            raise PermissionError("Identity policy explicitly denies one of the current groups")
        allowed = set(policy.allowed_groups_json or [])
        if allowed and not (allowed & effective_groups):
            raise PermissionError("Identity is not in an allowed group for this scoped action")
        if identity.is_service_account and not policy.allow_service_accounts:
            raise PermissionError("Service accounts are not permitted by this identity policy")

    # High-impact administrative/release actions retain the existing application-admin gate.
    if action in {"approval_policy_admin", "identity_policy_admin", "delegation_admin", "release_package_release", "handover_target_admin", "handover_execute"} and not is_engineering_admin(identity):
        raise PermissionError("Engineering Admin identity required")

    assurance = _assurance_payload(identity, max_age=max_age, required_acr=required_acr)
    return PolicyDecision(
        allowed=True,
        action=action,
        policy_id=policy.id if policy else None,
        effective_groups=sorted(effective_groups),
        delegation_ids=[d.id for d in delegations],
        reason="allowed",
        identity=identity_snapshot(identity),
        assurance=assurance,
    )


def apply_governance_rls_context(db: Session, identity: Identity) -> None:
    """Set PostgreSQL transaction-local governance identity context when optional RLS is enabled.

    v6.3.6 deliberately limits RLS to the new identity-policy/delegation tables. Existing
    project/area/document ACLs remain application-enforced until a dedicated RLS migration
    is certified against the corporate PostgreSQL role model.
    """
    cfg = get_settings()
    if not cfg.governance_postgres_rls_enabled or db.bind is None or db.bind.dialect.name != "postgresql":
        return
    db.execute(text("SELECT set_config('mgc.user', :v, true)"), {"v": identity.user})
    db.execute(text("SELECT set_config('mgc.is_admin', :v, true)"), {"v": "true" if is_engineering_admin(identity) else "false"})
