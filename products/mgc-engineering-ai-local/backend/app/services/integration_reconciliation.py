from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    BuildGenealogyItem,
    ConfigurationEffectivity,
    ExternalObject,
    ExternalSystem,
    IntegrationEntityMapping,
    IntegrationIngestEvent,
    IntegrationRun,
    ManufacturingBOMItem,
    PPAPSubmission,
    Part,
    ProcessDefect,
    ReleaseBaseline,
    VehicleBuild,
)
from app.services.integration_hardening import age_quality_snapshot, aggregate_system_quality
from app.services.release_baseline import compare_bom_rows

RECONCILIATION_VERSION = "mgc-reconciliation-v1"
ROLE_DEFAULTS = {"plm": "ebom", "pdm": "ebom", "erp": "mbom", "mes": "genealogy", "qms": "defects"}
VALID_ROLES = {"ebom", "mbom", "genealogy", "defects"}
VALID_ENTITY_TYPES = {"part", "vin", "supplier", "bom_position", "defect"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _meta(obj: ExternalObject) -> dict[str, Any]:
    value = obj.metadata_json or {}
    if isinstance(value.get("record"), dict):
        return {**value, **value["record"]}
    return value


def _first(meta: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        cur: Any = meta
        for piece in key.split("."):
            if not isinstance(cur, dict) or piece not in cur:
                cur = None
                break
            cur = cur[piece]
        if cur not in (None, "", [], {}):
            return cur
    return None


def system_reconciliation_role(system: ExternalSystem) -> str | None:
    cfg = system.config_json or {}
    rec = cfg.get("reconciliation") if isinstance(cfg.get("reconciliation"), dict) else {}
    explicit = str(rec.get("role") or cfg.get("reconciliation_role") or "").strip().lower()
    if explicit in VALID_ROLES:
        return explicit
    return ROLE_DEFAULTS.get(str(system.source_domain or "").lower())


def _system_project_scope(system: ExternalSystem) -> str | None:
    cfg = system.config_json or {}
    rec = cfg.get("reconciliation") if isinstance(cfg.get("reconciliation"), dict) else {}
    return str(rec.get("project_code") or cfg.get("project_code") or "").strip() or None


def _object_project(obj: ExternalObject) -> str | None:
    meta = _meta(obj)
    return str(_first(meta, "project_code", "project", "program_code") or "").strip() or None


def _project_ok(system: ExternalSystem, obj: ExternalObject, project_code: str) -> bool:
    configured = _system_project_scope(system)
    observed = _object_project(obj)
    if configured and configured != project_code:
        return False
    if observed and observed != project_code:
        return False
    return True


def _objects_for(db: Session, system: ExternalSystem, project_code: str) -> list[ExternalObject]:
    rows = db.scalars(select(ExternalObject).where(ExternalObject.system_id == system.id)).all()
    return [x for x in rows if _project_ok(system, x, project_code)]


def _bom_fact(obj: ExternalObject, system: ExternalSystem) -> dict[str, Any] | None:
    meta = _meta(obj)
    parent = _first(meta, "parent_part_number", "parent_part", "parent", "assembly_part_number")
    child = _first(meta, "child_part_number", "child_part", "component_part_number", "component", "part_number") or obj.part_number
    if not parent or not child:
        return None
    quantity = _first(meta, "quantity", "qty", "component_quantity")
    try:
        quantity = float(quantity if quantity is not None else 1.0)
    except (TypeError, ValueError):
        quantity = 1.0
    return {
        "parent_part_number": _norm(parent),
        "parent_revision": _first(meta, "parent_revision"),
        "child_part_number": _norm(child),
        "child_revision": _first(meta, "child_revision", "revision") or obj.revision,
        "quantity": quantity,
        "unit": str(_first(meta, "unit", "uom") or "pcs"),
        "description": _first(meta, "description", "name"),
        "position": str(_first(meta, "position", "find_number", "item_number") or "") or None,
        "supplier_code": _first(meta, "supplier_code", "supplier", "vendor_code"),
        "supplier_name": _first(meta, "supplier_name", "vendor_name"),
        "unit_cost": None,
        "currency": None,
        "source_system": system.code,
        "external_id": obj.external_id,
        "source_fingerprint": obj.source_fingerprint,
    }


def _genealogy_fact(obj: ExternalObject, system: ExternalSystem) -> dict[str, Any] | None:
    meta = _meta(obj)
    vin = _first(meta, "vehicle_identifier", "vin", "vehicle.vin", "serial_vehicle")
    part = _first(meta, "part_number", "component_part_number", "component.part_number") or obj.part_number
    if not vin or not part:
        return None
    return {
        "vehicle_identifier": _norm(vin),
        "part_number": _norm(part),
        "revision": _first(meta, "revision", "part_revision", "component.revision") or obj.revision,
        "supplier_code": _first(meta, "supplier_code", "supplier", "vendor_code"),
        "lot_number": _first(meta, "lot_number", "lot", "batch"),
        "serial_number": _first(meta, "serial_number", "component_serial"),
        "quantity": _first(meta, "quantity", "qty") or 1,
        "source_system": system.code,
        "external_id": obj.external_id,
    }


def _defect_fact(obj: ExternalObject, system: ExternalSystem) -> dict[str, Any] | None:
    meta = _meta(obj)
    defect_code = _first(meta, "defect_code", "failure_code", "nonconformance_code") or obj.external_id
    part = _first(meta, "part_number", "component_part_number") or obj.part_number
    vin = _first(meta, "vehicle_identifier", "vin")
    supplier = _first(meta, "supplier_code", "supplier", "vendor_code")
    if not defect_code:
        return None
    return {
        "defect_code": str(defect_code),
        "part_number": _norm(part) or None,
        "vehicle_identifier": _norm(vin) or None,
        "supplier_code": _norm(supplier) or None,
        "quantity": int(_first(meta, "quantity", "count") or 1),
        "severity": str(_first(meta, "severity", "priority") or "unknown"),
        "source_system": system.code,
        "external_id": obj.external_id,
    }


def source_facts(db: Session, project_code: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {role: [] for role in VALID_ROLES}
    systems = db.scalars(select(ExternalSystem).where(ExternalSystem.enabled == True)).all()  # noqa: E712
    for system in systems:
        role = system_reconciliation_role(system)
        if role not in VALID_ROLES:
            continue
        for obj in _objects_for(db, system, project_code):
            fact = _bom_fact(obj, system) if role in {"ebom", "mbom"} else (_genealogy_fact(obj, system) if role == "genealogy" else _defect_fact(obj, system))
            if fact:
                fact["system_id"] = system.id
                fact["data_confidence_level"] = obj.data_confidence_level or "UNKNOWN"
                fact["data_confidence_score"] = obj.data_confidence_score
                out[role].append(fact)
    for role in out:
        out[role].sort(key=lambda x: (x.get("source_system") or "", x.get("external_id") or ""))
    return out


def _canonical_sets(db: Session, project_code: str) -> dict[str, set[str]]:
    parts = {_norm(x.part_number) for x in db.scalars(select(Part).where(Part.project_code == project_code)).all() if x.part_number}
    for x in db.scalars(select(ManufacturingBOMItem).where(ManufacturingBOMItem.project_code == project_code)).all():
        parts.update({_norm(x.parent_part_number), _norm(x.child_part_number)})
    vins = {_norm(x.vehicle_identifier) for x in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code == project_code)).all() if x.vehicle_identifier}
    suppliers = {_norm(x.supplier_code) for x in db.scalars(select(ManufacturingBOMItem).where(ManufacturingBOMItem.project_code == project_code)).all() if x.supplier_code}
    suppliers |= {_norm(x.supplier_code) for x in db.scalars(select(PPAPSubmission).where(PPAPSubmission.project_code == project_code)).all() if x.supplier_code}
    build_ids = {x.id for x in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code == project_code)).all()}
    if build_ids:
        suppliers |= {_norm(x.supplier_code) for x in db.scalars(select(BuildGenealogyItem)).all() if x.build_id in build_ids and x.supplier_code}
    return {"part": {x for x in parts if x}, "vin": {x for x in vins if x}, "supplier": {x for x in suppliers if x}}


def canonical_target_exists(db: Session, project_code: str, entity_type: str, canonical_key: str) -> bool:
    key = _norm(canonical_key)
    if entity_type == "part":
        return key in _canonical_sets(db, project_code)["part"]
    if entity_type == "vin":
        return key in _canonical_sets(db, project_code)["vin"]
    if entity_type == "supplier":
        return key in _canonical_sets(db, project_code)["supplier"]
    if entity_type == "defect":
        return bool(db.scalar(select(ProcessDefect).where(ProcessDefect.project_code == project_code, ProcessDefect.defect_code == canonical_key)))
    if entity_type == "bom_position":
        return bool(db.scalar(select(ManufacturingBOMItem).where(ManufacturingBOMItem.project_code == project_code, ManufacturingBOMItem.position == canonical_key)))
    return False


def _mapping_lookup(db: Session, project_code: str) -> dict[tuple[str, str, str, str, str], IntegrationEntityMapping]:
    rows = db.scalars(select(IntegrationEntityMapping).where(
        (IntegrationEntityMapping.project_code == project_code) | (IntegrationEntityMapping.project_code.is_(None))
    )).all()
    return {(x.system_id, x.source_entity_type, x.source_external_id, _norm(x.source_key), x.canonical_entity_type): x for x in rows if x.status == "confirmed"}


def _mapping_is_stale(mapping: IntegrationEntityMapping, obj: ExternalObject | None, system: ExternalSystem, now: datetime) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if obj and mapping.source_fingerprint and obj.source_fingerprint and mapping.source_fingerprint != obj.source_fingerprint:
        reasons.append("SOURCE_FINGERPRINT_CHANGED")
    cfg = system.config_json or {}
    rec = cfg.get("reconciliation") if isinstance(cfg.get("reconciliation"), dict) else {}
    stale_minutes = rec.get("mapping_review_minutes")
    try:
        stale_minutes = int(stale_minutes) if stale_minutes is not None else None
    except (TypeError, ValueError):
        stale_minutes = None
    if stale_minutes and mapping.last_verified_at:
        age = (now - _aware(mapping.last_verified_at)).total_seconds() / 60.0
        if age > stale_minutes:
            reasons.append("MAPPING_REVIEW_OVERDUE")
    return bool(reasons), reasons


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _object_by_id(db: Session, system_id: str, external_id: str) -> ExternalObject | None:
    return db.scalar(select(ExternalObject).where(ExternalObject.system_id == system_id, ExternalObject.external_id == external_id))


def resolve_reference(
    db: Session,
    *,
    project_code: str,
    system: ExternalSystem,
    external_id: str,
    entity_type: str,
    source_key: str | None,
    canonical_sets: dict[str, set[str]],
    mappings: dict[tuple[str, str, str, str, str], IntegrationEntityMapping],
    now: datetime,
) -> dict[str, Any]:
    key = _norm(source_key)
    canonical = canonical_sets.get(entity_type, set())
    if key and key in canonical:
        return {"status": "EXACT", "canonical_key": key, "mapping_id": None, "stale": False, "reasons": []}
    mapping = mappings.get((system.id, entity_type, external_id, key, entity_type))
    if not mapping:
        return {"status": "UNMATCHED", "canonical_key": None, "mapping_id": None, "stale": False, "reasons": []}
    obj = _object_by_id(db, system.id, external_id)
    stale, reasons = _mapping_is_stale(mapping, obj, system, now)
    target = _norm(mapping.canonical_key)
    if target not in canonical:
        return {"status": "BROKEN_MAPPING", "canonical_key": target or None, "mapping_id": mapping.id, "stale": True, "reasons": [*reasons, "CANONICAL_TARGET_MISSING"]}
    return {"status": "STALE" if stale else "MAPPED", "canonical_key": target, "mapping_id": mapping.id, "stale": stale, "reasons": reasons}


def mapping_coverage(db: Session, project_code: str, facts: dict[str, list[dict[str, Any]]], now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    systems = {x.id: x for x in db.scalars(select(ExternalSystem)).all()}
    canonical = _canonical_sets(db, project_code)
    mappings = _mapping_lookup(db, project_code)
    refs: list[dict[str, Any]] = []

    def add(fact: dict[str, Any], entity_type: str, source_key: str | None):
        system = systems.get(fact.get("system_id"))
        if not system or not source_key:
            return
        state = resolve_reference(db, project_code=project_code, system=system, external_id=str(fact["external_id"]), entity_type=entity_type, source_key=source_key, canonical_sets=canonical, mappings=mappings, now=now)
        refs.append({"system": system.code, "system_id": system.id, "external_id": fact["external_id"], "entity_type": entity_type, "source_key": source_key, **state})

    for role, rows in facts.items():
        for fact in rows:
            if role in {"ebom", "mbom"}:
                add(fact, "part", fact.get("parent_part_number")); add(fact, "part", fact.get("child_part_number"))
                add(fact, "supplier", fact.get("supplier_code"))
            elif role == "genealogy":
                add(fact, "vin", fact.get("vehicle_identifier")); add(fact, "part", fact.get("part_number")); add(fact, "supplier", fact.get("supplier_code"))
            elif role == "defects":
                add(fact, "vin", fact.get("vehicle_identifier")); add(fact, "part", fact.get("part_number")); add(fact, "supplier", fact.get("supplier_code"))
    # De-duplicate repeated references without hiding different external source objects.
    unique = {(r["system_id"], r["external_id"], r["entity_type"], _norm(r["source_key"])): r for r in refs}
    refs = list(unique.values())
    resolved = [r for r in refs if r["status"] in {"EXACT", "MAPPED"}]
    stale = [r for r in refs if r["status"] in {"STALE", "BROKEN_MAPPING"}]
    unmatched = [r for r in refs if r["status"] == "UNMATCHED"]
    coverage = len(resolved) / len(refs) if refs else 0.0
    by_type = {}
    for typ in ("part", "vin", "supplier"):
        typed = [r for r in refs if r["entity_type"] == typ]
        typed_resolved = [r for r in typed if r["status"] in {"EXACT", "MAPPED"}]
        by_type[typ] = {"total": len(typed), "resolved": len(typed_resolved), "coverage": round(len(typed_resolved) / len(typed), 4) if typed else None}
    return {
        "total_references": len(refs),
        "resolved": len(resolved),
        "stale": len(stale),
        "unmatched": len(unmatched),
        "coverage": round(coverage, 4),
        "by_entity_type": by_type,
        "stale_mappings": stale[:200],
        "unmatched_entities": unmatched[:200],
        "exact_matches_do_not_require_mapping_rows": True,
    }


def canonicalize_source_facts(db: Session, project_code: str, facts: dict[str, list[dict[str, Any]]], now: datetime | None = None) -> dict[str, list[dict[str, Any]]]:
    """Apply only exact or human-confirmed, non-stale identifier mappings to a report copy.

    Source records are never mutated. Stale/broken/unmatched mappings remain unresolved and
    therefore cannot silently make a reconciliation look green.
    """
    now = now or utcnow()
    systems = {x.id: x for x in db.scalars(select(ExternalSystem)).all()}
    canonical = _canonical_sets(db, project_code)
    mappings = _mapping_lookup(db, project_code)
    out: dict[str, list[dict[str, Any]]] = {role: [] for role in VALID_ROLES}
    fields = {
        "ebom": (("parent_part_number", "part"), ("child_part_number", "part"), ("supplier_code", "supplier")),
        "mbom": (("parent_part_number", "part"), ("child_part_number", "part"), ("supplier_code", "supplier")),
        "genealogy": (("vehicle_identifier", "vin"), ("part_number", "part"), ("supplier_code", "supplier")),
        "defects": (("vehicle_identifier", "vin"), ("part_number", "part"), ("supplier_code", "supplier")),
    }
    for role, rows in facts.items():
        for row in rows:
            item = dict(row); resolution = {}
            system = systems.get(row.get("system_id"))
            if system:
                for field, entity_type in fields.get(role, ()):
                    source_key = item.get(field)
                    if not source_key: continue
                    state = resolve_reference(db, project_code=project_code, system=system, external_id=str(item["external_id"]), entity_type=entity_type, source_key=str(source_key), canonical_sets=canonical, mappings=mappings, now=now)
                    resolution[field] = state
                    if state["status"] in {"EXACT", "MAPPED"} and state.get("canonical_key"):
                        item[field] = state["canonical_key"]
            item["mapping_resolution"] = resolution
            out[role].append(item)
    return out


def reconcile_ebom_mbom_sources(facts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ebom = facts.get("ebom") or []
    mbom = facts.get("mbom") or []
    if not ebom or not mbom:
        return {
            "status": "NOT_CONFIGURED",
            "configured": False,
            "ebom_rows": len(ebom),
            "mbom_rows": len(mbom),
            "missing_source_roles": [x for x, rows in (("ebom", ebom), ("mbom", mbom)) if not rows],
            "advisory_only": True,
        }
    diff = compare_bom_rows(ebom, mbom)
    return {
        "status": "MISMATCH" if diff["has_changes"] else "MATCH",
        "configured": True,
        "ebom_rows": len(ebom),
        "mbom_rows": len(mbom),
        "ebom_systems": sorted({x["source_system"] for x in ebom}),
        "mbom_systems": sorted({x["source_system"] for x in mbom}),
        "summary": diff["summary"],
        "added_in_mbom": diff["added"][:200],
        "missing_in_mbom": diff["removed"][:200],
        "replacements": diff["replaced"][:200],
        "moved": diff["moved"][:200],
        "changed": diff["changed"][:200],
        "advisory_only": True,
        "no_automatic_source_write": True,
    }


def _vin_in_range(vin: str, start: str | None, end: str | None) -> bool:
    value = _norm(vin)
    if start and value < _norm(start):
        return False
    if end and value > _norm(end):
        return False
    return True


def _effectivity_expected(db: Session, build: VehicleBuild, part_number: str) -> set[str]:
    rows = db.scalars(select(ConfigurationEffectivity).where(
        ConfigurationEffectivity.project_code == build.project_code,
        ConfigurationEffectivity.part_number == part_number,
        ConfigurationEffectivity.status == "active",
    )).all()
    expected: set[str] = set()
    built_at = _aware(build.completed_at) if build.completed_at else None
    for r in rows:
        if r.variant_id and r.variant_id != build.variant_id: continue
        if r.plant and _norm(r.plant) != _norm(build.plant): continue
        if not _vin_in_range(build.vehicle_identifier, r.vin_from, r.vin_to): continue
        if r.effective_from and (not built_at or built_at < _aware(r.effective_from)): continue
        if r.effective_to and (not built_at or built_at > _aware(r.effective_to)): continue
        if r.revision: expected.add(str(r.revision))
    return expected


def _baseline_expected(db: Session, build: VehicleBuild, part_number: str) -> set[str]:
    if not build.release_baseline_id:
        return set()
    base = db.get(ReleaseBaseline, build.release_baseline_id)
    if not base:
        return set()
    snap = base.snapshot_json or {}
    rows = list(snap.get("manufacturing_bom") or []) + list(snap.get("bom") or [])
    expected = set()
    for row in rows:
        if _norm(row.get("child_part_number")) == part_number and row.get("child_revision"):
            expected.add(str(row["child_revision"]))
    return expected


def reconcile_mes_genealogy(db: Session, project_code: str, facts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = facts.get("genealogy") or []
    if not rows:
        return {"status": "NOT_CONFIGURED", "configured": False, "observations": 0, "advisory_only": True}
    builds = {_norm(x.vehicle_identifier): x for x in db.scalars(select(VehicleBuild).where(VehicleBuild.project_code == project_code)).all()}
    matched = []; mismatches = []; unresolved = []
    for row in rows:
        build = builds.get(_norm(row.get("vehicle_identifier")))
        if not build:
            unresolved.append({**row, "reason": "VIN_NOT_MAPPED_TO_BUILD"}); continue
        part = _norm(row.get("part_number"))
        expected = _baseline_expected(db, build, part) or _effectivity_expected(db, build, part)
        if not expected:
            unresolved.append({**row, "build_id": build.id, "reason": "RELEASED_REVISION_NOT_PROVABLE"}); continue
        observed = str(row.get("revision") or "")
        item = {**row, "build_id": build.id, "expected_revisions": sorted(expected)}
        if observed and observed in expected:
            matched.append(item)
        else:
            mismatches.append({**item, "reason": "REVISION_MISMATCH"})
    status = "MISMATCH" if mismatches else ("REVIEW_REQUIRED" if unresolved else "MATCH")
    return {
        "status": status,
        "configured": True,
        "observations": len(rows),
        "matched": len(matched),
        "mismatches": len(mismatches),
        "unresolved": len(unresolved),
        "mismatch_items": mismatches[:200],
        "unresolved_items": unresolved[:200],
        "comparison": "MES genealogy vs released baseline/effectivity",
        "advisory_only": True,
        "no_mes_write": True,
    }


def reconcile_qms_links(db: Session, project_code: str, facts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = facts.get("defects") or []
    if not rows:
        return {"status": "NOT_CONFIGURED", "configured": False, "records": 0, "advisory_only": True}
    canonical = _canonical_sets(db, project_code)
    linked=[]; partial=[]; unmatched=[]
    for row in rows:
        checks = {}
        for typ, field in (("part", "part_number"), ("vin", "vehicle_identifier"), ("supplier", "supplier_code")):
            value = _norm(row.get(field))
            if value:
                checks[typ] = value in canonical.get(typ, set())
        if checks and all(checks.values()):
            linked.append({**row, "links": checks})
        elif any(checks.values()):
            partial.append({**row, "links": checks})
        else:
            unmatched.append({**row, "links": checks})
    status = "MATCH" if not partial and not unmatched else "REVIEW_REQUIRED"
    return {
        "status": status,
        "configured": True,
        "records": len(rows),
        "fully_linked": len(linked),
        "partial": len(partial),
        "unmatched": len(unmatched),
        "link_coverage": round(len(linked) / len(rows), 4) if rows else 0.0,
        "partial_items": partial[:200],
        "unmatched_items": unmatched[:200],
        "link_target": "Part / VIN / Supplier",
        "advisory_only": True,
        "no_qms_write": True,
    }


def authority_conflicts(db: Session, project_code: str, facts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    systems = [x for x in db.scalars(select(ExternalSystem).where(ExternalSystem.enabled == True)).all() if not _system_project_scope(x) or _system_project_scope(x) == project_code]  # noqa: E712
    claims: dict[str, list[str]] = defaultdict(list)
    for system in systems:
        cfg = system.config_json or {}; rec = cfg.get("reconciliation") if isinstance(cfg.get("reconciliation"), dict) else {}
        for role in rec.get("authoritative_for", []) if isinstance(rec.get("authoritative_for"), list) else []:
            if str(role).lower() in VALID_ROLES:
                claims[str(role).lower()].append(system.code)
    explicit = [{"role": role, "systems": sorted(codes), "reason": "MULTIPLE_EXPLICIT_AUTHORITIES"} for role, codes in claims.items() if len(codes) > 1]

    revision_conflicts=[]
    for role in ("ebom", "mbom"):
        by_part: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        for row in facts.get(role) or []:
            rev = str(row.get("child_revision") or "")
            if rev: by_part[row["child_part_number"]][row["source_system"]].add(rev)
        for part, by_system in by_part.items():
            revisions = sorted({r for vals in by_system.values() for r in vals})
            if len(revisions) > 1 and len(by_system) > 1:
                revision_conflicts.append({"role": role, "part_number": part, "systems": {k: sorted(v) for k,v in sorted(by_system.items())}, "revisions": revisions})
    return {
        "status": "CONFLICT" if explicit or revision_conflicts else "CLEAR",
        "explicit_authority_conflicts": explicit,
        "cross_source_revision_conflicts": revision_conflicts[:200],
        "no_automatic_winner_selection": True,
    }


def integration_slo(db: Session, project_code: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    systems = [x for x in db.scalars(select(ExternalSystem).where(ExternalSystem.enabled == True)).all() if system_reconciliation_role(x) and (not _system_project_scope(x) or _system_project_scope(x) == project_code)]  # noqa: E712
    system_rows=[]; successful_runs=total_runs=0; fresh_ok=0
    for system in systems:
        objects = _objects_for(db, system, project_code)
        quarantine = int(db.scalar(select(func.count()).select_from(IntegrationIngestEvent).where(IntegrationIngestEvent.system_id == system.id, IntegrationIngestEvent.status == "quarantined")) or 0)
        quality = aggregate_system_quality(objects, expected_freshness_minutes=system.expected_freshness_minutes, quarantined=quarantine, failed=0, now=now)
        runs = db.scalars(select(IntegrationRun).where(IntegrationRun.system_id == system.id).order_by(IntegrationRun.started_at.desc()).limit(20)).all()
        total_runs += len(runs); successful_runs += sum(1 for r in runs if r.status == "ok")
        freshness_counts = quality.get("freshness_status_counts") or {}
        source_fresh = not any(k in freshness_counts for k in ("STALE", "UNKNOWN")) if objects else False
        if source_fresh: fresh_ok += 1
        system_rows.append({
            "system": system.code,
            "role": system_reconciliation_role(system),
            "quality_level": quality.get("level"),
            "quality_score": quality.get("score"),
            "freshness_compliant": source_fresh,
            "last_sync_status": system.last_sync_status,
            "quarantined": quarantine,
            "objects": len(objects),
            "recent_runs": len(runs),
            "successful_runs": sum(1 for r in runs if r.status == "ok"),
        })
    return {
        "systems": system_rows,
        "source_count": len(systems),
        "freshness_compliance": round(fresh_ok / len(systems), 4) if systems else 0.0,
        "sync_success_rate": round(successful_runs / total_runs, 4) if total_runs else None,
        "recent_runs": total_runs,
        "quarantined_total": sum(x["quarantined"] for x in system_rows),
    }


def pilot_acceptance(report: dict[str, Any], *, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or {}
    required_roles = set(policy.get("required_roles") or ["ebom", "mbom", "genealogy", "defects"])
    min_mapping = float(policy.get("min_mapping_coverage", 0.95))
    min_freshness = float(policy.get("min_freshness_compliance", 0.95))
    min_sync = float(policy.get("min_sync_success_rate", 0.95))
    configured_roles = {role for role, rows in (report.get("source_counts") or {}).items() if int(rows or 0) > 0}
    criteria=[]
    def add(code: str, ok: bool, actual: Any, expected: Any, severity: str="blocker"):
        criteria.append({"code": code, "pass": bool(ok), "actual": actual, "expected": expected, "severity": severity})
    add("REQUIRED_SOURCE_ROLES", required_roles.issubset(configured_roles), sorted(configured_roles), sorted(required_roles))
    cov = float((report.get("mapping_coverage") or {}).get("coverage") or 0)
    add("MAPPING_COVERAGE", cov >= min_mapping, cov, f">={min_mapping:.2f}")
    add("STALE_MAPPINGS", int((report.get("mapping_coverage") or {}).get("stale") or 0) == 0, int((report.get("mapping_coverage") or {}).get("stale") or 0), 0)
    qms_cov = (report.get("qms_entity_linkage") or {}).get("link_coverage")
    add("QMS_LINKAGE", qms_cov is not None and float(qms_cov) >= min_mapping, qms_cov, f">={min_mapping:.2f}")
    slo = report.get("integration_slo") or {}
    freshness = float(slo.get("freshness_compliance") or 0)
    add("FRESHNESS_COMPLIANCE", freshness >= min_freshness, freshness, f">={min_freshness:.2f}")
    sync = slo.get("sync_success_rate")
    add("SYNC_SUCCESS_RATE", sync is not None and float(sync) >= min_sync, sync, f">={min_sync:.2f}")
    add("QUARANTINE_EMPTY", int(slo.get("quarantined_total") or 0) == 0, int(slo.get("quarantined_total") or 0), 0)
    low_sources = sorted(x["system"] for x in (slo.get("systems") or []) if x.get("quality_level") in {"LOW", "UNKNOWN"})
    add("DATA_CONFIDENCE", not low_sources, low_sources, "no LOW/UNKNOWN required sources")
    auth = report.get("source_of_truth_conflicts") or {}
    add("SOURCE_AUTHORITY_CLEAR", auth.get("status") != "CONFLICT", auth.get("status"), "CLEAR")
    for name in ("ebom_vs_mbom", "mes_vs_released_configuration"):
        status = (report.get(name) or {}).get("status")
        add(name.upper(), status == "MATCH", status, "MATCH")
    blockers=[x for x in criteria if not x["pass"] and x["severity"]=="blocker"]
    return {
        "status": "READY_FOR_CONTROLLED_PILOT" if not blockers else "NOT_READY",
        "criteria": criteria,
        "blockers": blockers,
        "human_go_live_approval_required": True,
        "not_a_production_release": True,
        "policy": {"required_roles": sorted(required_roles), "min_mapping_coverage": min_mapping, "min_freshness_compliance": min_freshness, "min_sync_success_rate": min_sync},
    }


def build_reconciliation_report(db: Session, project_code: str, *, now: datetime | None = None, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    now = now or utcnow()
    facts = source_facts(db, project_code)
    canonical_facts = canonicalize_source_facts(db, project_code, facts, now)
    report = {
        "schema": RECONCILIATION_VERSION,
        "project_code": project_code,
        "generated_at": now.isoformat(),
        "source_counts": {k: len(v) for k,v in sorted(facts.items())},
        "mapping_coverage": mapping_coverage(db, project_code, facts, now),
        "ebom_vs_mbom": reconcile_ebom_mbom_sources(canonical_facts),
        "mes_vs_released_configuration": reconcile_mes_genealogy(db, project_code, canonical_facts),
        "qms_entity_linkage": reconcile_qms_links(db, project_code, canonical_facts),
        "source_of_truth_conflicts": authority_conflicts(db, project_code, canonical_facts),
        "integration_slo": integration_slo(db, project_code, now),
        "governance": {
            "read_only_reconciliation": True,
            "no_automatic_source_system_write": True,
            "no_automatic_mapping_confirmation": True,
            "human_conflict_resolution_required": True,
        },
    }
    report["pilot_acceptance"] = pilot_acceptance(report, policy=policy)
    return report
