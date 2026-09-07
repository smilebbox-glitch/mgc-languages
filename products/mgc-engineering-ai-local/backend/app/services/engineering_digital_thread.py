from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode,
    BOMItem,
    ChangeRequest,
    ConfigurationApplicability,
    CostBaseline,
    CostLine,
    Document,
    EngineeringRequirement,
    InterfaceDefinition,
    LocalizationItem,
    ManufacturingLine,
    Part,
    ProcessOperation,
    ProcessStation,
    ReleaseBaseline,
    RequirementVerification,
    ValidationIssue,
    VehicleVariant,
)


TERMINAL_CHANGE = {"implemented", "rejected", "cancelled"}


def _status(value) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _area_ok(area: str | None, requested: str | None, allowed: set[str]) -> bool:
    if area and area not in allowed:
        return False
    if requested:
        return area in {None, requested}
    return True


def _doc_ok(ids: Iterable[str] | None, visible_document_ids: set[str]) -> bool:
    values = set(ids or [])
    return not values or values.issubset(visible_document_ids)


def engineering_digital_thread(
    db: Session,
    project_code: str,
    visible_document_ids: set[str],
    visible_part_numbers: set[str],
    manufacturing_area: str | None = None,
    allowed_area_codes: set[str] | None = None,
    focus_part: str | None = None,
    depth: int = 3,
    max_nodes: int = 280,
) -> dict:
    """Build a deterministic, ACL-safe cross-domain engineering graph.

    The graph is a navigation/evidence layer. It does not infer missing relationships,
    change PLM/ERP data, or grant product/process release authority.
    """
    allowed = set(allowed_area_codes or [])
    depth = max(1, min(int(depth), 5))
    max_nodes = max(50, min(int(max_nodes), 500))
    focus = focus_part.strip().upper() if focus_part else None
    if focus and focus not in visible_part_numbers:
        raise LookupError("Part not found")

    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    gaps: list[dict] = []
    part_domains: dict[str, set[str]] = {pn: set() for pn in visible_part_numbers}

    def node(kind: str, raw_id: str, label: str, *, status: str | None = None, part_number: str | None = None,
             manufacturing_area: str | None = None, meta: dict | None = None) -> str:
        nid = f"{kind}:{raw_id}"
        if nid not in nodes:
            nodes[nid] = {
                "id": nid,
                "type": kind,
                "key": raw_id,
                "label": label,
                "status": status,
                "part_number": part_number,
                "manufacturing_area": manufacturing_area,
                "meta": meta or {},
            }
        return nid

    def edge(source: str, target: str, relation: str, label: str, *, critical: bool = False, meta: dict | None = None) -> None:
        if source not in nodes or target not in nodes:
            return
        eid = f"{source}|{relation}|{target}"
        edges[eid] = {
            "id": eid,
            "source": source,
            "target": target,
            "relation": relation,
            "label": label,
            "critical": bool(critical),
            "meta": meta or {},
        }

    # Parts are included only when backed by visible project evidence.
    part_rows = db.scalars(select(Part).where(Part.project_code == project_code, Part.part_number.in_(visible_part_numbers))).all() if visible_part_numbers else []
    part_names = {p.part_number: p.name for p in part_rows}
    for pn in sorted(visible_part_numbers):
        node("part", pn, f"{pn}{' · ' + part_names[pn] if part_names.get(pn) else ''}", part_number=pn)

    docs = [d for d in db.scalars(select(Document).where(Document.project_code == project_code)).all()
            if d.id in visible_document_ids and _area_ok(d.manufacturing_area, manufacturing_area, allowed)]
    docs_by_id = {d.id: d for d in docs}
    doc_types_by_part: dict[str, set[str]] = defaultdict(set)
    for d in docs:
        did = node("document", d.id, d.filename, status=_status(d.status), part_number=d.part_number,
                   manufacturing_area=d.manufacturing_area,
                   meta={"doc_type": d.doc_type or "document", "revision": d.revision, "sha256": d.sha256})
        if d.part_number and d.part_number in visible_part_numbers:
            pid = f"part:{d.part_number}"
            edge(pid, did, "HAS_DOCUMENT", "документирует")
            part_domains[d.part_number].add("documents")
            doc_types_by_part[d.part_number].add(d.doc_type or "document")

    # Product structure from visible BOM source documents only.
    bom_rows = [b for b in db.scalars(select(BOMItem)).all() if b.source_document_id in docs_by_id]
    for b in bom_rows:
        if b.parent_part_number not in visible_part_numbers:
            continue
        parent = f"part:{b.parent_part_number}"
        if b.child_part_number in visible_part_numbers:
            child = f"part:{b.child_part_number}"
            edge(parent, child, "BOM_CONTAINS", "BOM", meta={"quantity": b.quantity, "unit": b.unit, "position": b.position,
                                                               "parent_revision": b.parent_revision, "child_revision": b.child_revision,
                                                               "source_document_id": b.source_document_id})
            part_domains[b.parent_part_number].add("product_structure")
            part_domains[b.child_part_number].add("product_structure")
        else:
            gaps.append({"type": "bom_documentation", "severity": "warning", "part_number": b.parent_part_number,
                         "title": f"{b.child_part_number}: позиция BOM видна, но карточка детали не подтверждена доступной документацией"})

    # Requirements and V&V.
    requirements = []
    for r in db.scalars(select(EngineeringRequirement).where(EngineeringRequirement.project_code == project_code)).all():
        if not _area_ok(r.manufacturing_area, manufacturing_area, allowed):
            continue
        if r.source_document_id and r.source_document_id not in visible_document_ids:
            continue
        linked_parts = [pn.upper() for pn in (r.part_numbers or []) if pn.upper() in visible_part_numbers]
        if r.part_numbers and not linked_parts:
            continue
        rid = node("requirement", r.id, f"{r.code} · {r.title}", status=r.status, manufacturing_area=r.manufacturing_area,
                   meta={"code": r.code, "criticality": r.criticality, "verification_method": r.verification_method})
        requirements.append(r)
        for pn in linked_parts:
            edge(f"part:{pn}", rid, "HAS_REQUIREMENT", "требование", critical=r.criticality in {"critical", "safety", "regulatory"})
            part_domains[pn].add("requirements")
        if r.source_document_id and f"document:{r.source_document_id}" in nodes:
            edge(rid, f"document:{r.source_document_id}", "SOURCED_FROM", "источник")
        if not linked_parts:
            gaps.append({"type": "requirement_trace", "severity": "warning", "id": r.id,
                         "title": f"{r.code}: требование не связано ни с одной доступной деталью"})
    req_by_id = {r.id: r for r in requirements}
    ver_by_req: dict[str, list[RequirementVerification]] = defaultdict(list)
    for v in db.scalars(select(RequirementVerification).where(RequirementVerification.project_code == project_code)).all():
        if v.requirement_id not in req_by_id or not _area_ok(v.manufacturing_area, manufacturing_area, allowed):
            continue
        if not _doc_ok(v.evidence_document_ids, visible_document_ids):
            continue
        vid = node("verification", v.id, f"{v.code} · {v.title}", status=v.status, manufacturing_area=v.manufacturing_area,
                   meta={"phase": v.phase, "verification_type": v.verification_type})
        edge(f"requirement:{v.requirement_id}", vid, "VERIFIED_BY", "проверяется")
        for doc_id in v.evidence_document_ids or []:
            if f"document:{doc_id}" in nodes:
                edge(vid, f"document:{doc_id}", "EVIDENCED_BY", "evidence")
        ver_by_req[v.requirement_id].append(v)
        if v.status == "passed" and not (v.evidence_document_ids or []):
            gaps.append({"type": "verification_evidence", "severity": "warning", "id": v.id,
                         "title": f"{v.code}: PASSED без доступного evidence-документа"})
    for r in requirements:
        if r.status == "active" and not ver_by_req.get(r.id):
            gaps.append({"type": "requirement_verification", "severity": "critical" if r.criticality in {"critical", "safety", "regulatory"} else "warning",
                         "id": r.id, "title": f"{r.code}: нет связанной V&V записи"})

    # Manufacturing process: Part -> Operation -> Work Instruction.
    lines = [x for x in db.scalars(select(ManufacturingLine).where(ManufacturingLine.project_code == project_code)).all()
             if _area_ok(x.manufacturing_area, manufacturing_area, allowed)]
    line_by_id = {x.id: x for x in lines}
    stations = db.scalars(select(ProcessStation).where(ProcessStation.line_id.in_(set(line_by_id)))).all() if line_by_id else []
    station_by_id = {x.id: x for x in stations}
    operations = db.scalars(select(ProcessOperation).where(ProcessOperation.station_id.in_(set(station_by_id)))).all() if station_by_id else []
    for op in operations:
        if not op.part_number or op.part_number not in visible_part_numbers:
            continue
        st = station_by_id[op.station_id]; ln = line_by_id[st.line_id]
        oid = node("operation", op.id, f"{ln.code}/{st.code} · {op.code} · {op.name}", status=op.status,
                   part_number=op.part_number, manufacturing_area=ln.manufacturing_area,
                   meta={"line": ln.code, "station": st.code, "cycle_time_sec": op.cycle_time_sec, "operation_type": op.operation_type})
        edge(f"part:{op.part_number}", oid, "MANUFACTURED_BY", "операция")
        part_domains[op.part_number].add("process")
        visible_wi = [x for x in (op.work_instruction_document_ids or []) if x in visible_document_ids and f"document:{x}" in nodes]
        for doc_id in visible_wi:
            edge(oid, f"document:{doc_id}", "WORK_INSTRUCTION", "рабочая инструкция")
        if not visible_wi:
            gaps.append({"type": "process_instruction", "severity": "warning", "id": op.id, "part_number": op.part_number,
                         "title": f"{op.code}: операция не связана с доступной рабочей инструкцией"})

    # Supplier/localization.
    for s in db.scalars(select(LocalizationItem).where(LocalizationItem.project_code == project_code)).all():
        if s.part_number not in visible_part_numbers or not _area_ok(s.manufacturing_area, manufacturing_area, allowed):
            continue
        if not _doc_ok(s.evidence_document_ids, visible_document_ids):
            continue
        supplier_key = s.supplier_code or s.id
        sid = node("supplier", supplier_key, f"{s.supplier_code or 'SUP'} · {s.supplier_name}", status=s.status,
                   part_number=s.part_number, manufacturing_area=s.manufacturing_area,
                   meta={"localization_percent": s.localization_percent, "capacity_status": s.capacity_status,
                         "tooling_status": s.tooling_status, "item_id": s.id})
        edge(sid, f"part:{s.part_number}", "SUPPLIES", "поставляет")
        part_domains[s.part_number].add("supplier")
        for doc_id in s.evidence_document_ids or []:
            if f"document:{doc_id}" in nodes:
                edge(sid, f"document:{doc_id}", "EVIDENCED_BY", "evidence")
        if not (s.evidence_document_ids or []):
            gaps.append({"type": "supplier_evidence", "severity": "warning", "id": s.id, "part_number": s.part_number,
                         "title": f"{s.supplier_name}: supplier/localization запись без evidence-документа"})

    # Engineering economics. Cost is intentionally separate from ERP authority.
    cost_baselines = {x.id: x for x in db.scalars(select(CostBaseline).where(CostBaseline.project_code == project_code)).all()
                      if _area_ok(x.manufacturing_area, manufacturing_area, allowed)
                      and _doc_ok(x.evidence_document_ids, visible_document_ids)}
    for c in db.scalars(select(CostLine).where(CostLine.project_code == project_code)).all():
        if c.part_number not in visible_part_numbers or c.baseline_id not in cost_baselines or not _area_ok(c.manufacturing_area, manufacturing_area, allowed):
            continue
        if not _doc_ok(c.evidence_document_ids, visible_document_ids):
            continue
        base = cost_baselines[c.baseline_id]
        cid = node("cost", c.id, f"{base.code} · {c.part_number}", status=base.status, part_number=c.part_number,
                   manufacturing_area=c.manufacturing_area,
                   meta={"baseline_code": base.code, "baseline_type": base.baseline_type, "currency": base.currency,
                         "supplier_unit_price": c.supplier_unit_price, "target_unit_cost": c.target_unit_cost,
                         "mass_kg": c.mass_kg, "calculation_mode": c.calculation_mode})
        edge(f"part:{c.part_number}", cid, "HAS_COST", "engineering cost")
        part_domains[c.part_number].add("cost")
        for doc_id in c.evidence_document_ids or []:
            if f"document:{doc_id}" in nodes:
                edge(cid, f"document:{doc_id}", "EVIDENCED_BY", "evidence")

    # ECR/ECO and deterministic validation issues.
    for c in db.scalars(select(ChangeRequest).order_by(ChangeRequest.updated_at.desc())).all():
        if not c.part_number or c.part_number not in visible_part_numbers:
            continue
        if not _doc_ok(c.affected_document_ids, visible_document_ids):
            continue
        cid = node("change", c.id, f"{c.eco_code or c.code} · {c.title}", status=c.status, part_number=c.part_number,
                   meta={"code": c.code, "eco_code": c.eco_code, "from_revision": c.from_revision, "to_revision": c.to_revision,
                         "risk_level": c.risk_level, "priority": c.priority, "active": c.status not in TERMINAL_CHANGE})
        edge(f"part:{c.part_number}", cid, "CHANGED_BY", "ECR/ECO", critical=c.risk_level == "critical")
        part_domains[c.part_number].add("change")

    for i in db.scalars(select(ValidationIssue)).all():
        if not i.part_number or i.part_number not in visible_part_numbers:
            continue
        if not _doc_ok(i.document_ids, visible_document_ids):
            continue
        iid = node("issue", i.id, i.title, status=_status(i.status), part_number=i.part_number,
                   meta={"rule_code": i.rule_code, "severity": _status(i.severity)})
        edge(f"part:{i.part_number}", iid, "HAS_ISSUE", "замечание", critical=_status(i.severity) == "critical")
        part_domains[i.part_number].add("quality")
        for doc_id in i.document_ids or []:
            if f"document:{doc_id}" in nodes:
                edge(iid, f"document:{doc_id}", "FOUND_IN", "найдено в")

    # Vehicle architecture and interfaces.
    arch_rows = []
    for a in db.scalars(select(ArchitectureNode).where(ArchitectureNode.project_code == project_code)).all():
        if not _area_ok(a.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(a.evidence_document_ids, visible_document_ids):
            continue
        if a.part_number and a.part_number not in visible_part_numbers:
            continue
        aid = node("architecture", a.id, f"{a.code} · {a.name}", status=a.status, part_number=a.part_number,
                   manufacturing_area=a.manufacturing_area, meta={"code": a.code, "node_type": a.node_type})
        arch_rows.append(a)
        if a.part_number:
            edge(f"part:{a.part_number}", aid, "REPRESENTED_BY", "архитектура")
            part_domains[a.part_number].add("architecture")
    arch_ids = {a.id for a in arch_rows}
    for itf in db.scalars(select(InterfaceDefinition).where(InterfaceDefinition.project_code == project_code)).all():
        if itf.source_node_id not in arch_ids or itf.target_node_id not in arch_ids:
            continue
        if not _area_ok(itf.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(itf.evidence_document_ids, visible_document_ids):
            continue
        iid = node("interface", itf.id, f"{itf.code} · {itf.name}", status=itf.status, manufacturing_area=itf.manufacturing_area,
                   meta={"interface_type": itf.interface_type, "criticality": itf.criticality})
        edge(f"architecture:{itf.source_node_id}", iid, "INTERFACE", "интерфейс", critical=itf.criticality in {"critical", "safety"})
        edge(iid, f"architecture:{itf.target_node_id}", "CONNECTS_TO", "связывает", critical=itf.criticality in {"critical", "safety"})
        for rid in itf.requirement_ids or []:
            if f"requirement:{rid}" in nodes:
                edge(iid, f"requirement:{rid}", "TRACED_TO", "требование")

    # Vehicle configurations. UNKNOWN stays explicit by absence of an INCLUDED edge.
    variants = []
    for v in db.scalars(select(VehicleVariant).where(VehicleVariant.project_code == project_code)).all():
        if not _area_ok(v.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(v.evidence_document_ids, visible_document_ids):
            continue
        vid = node("variant", v.id, f"{v.code} · {v.name}", status=v.status, manufacturing_area=v.manufacturing_area,
                   meta={"model_year": v.model_year, "market": v.market, "body_style": v.body_style, "engine": v.engine, "transmission": v.transmission, "trim": v.trim})
        variants.append(v)
    variant_ids = {v.id for v in variants}
    for a in db.scalars(select(ConfigurationApplicability).where(ConfigurationApplicability.project_code == project_code, ConfigurationApplicability.entity_type == "part")).all():
        pn = a.entity_key.upper()
        if a.variant_id not in variant_ids or pn not in visible_part_numbers:
            continue
        if not _area_ok(a.manufacturing_area, manufacturing_area, allowed) or not _doc_ok(a.evidence_document_ids, visible_document_ids):
            continue
        edge(f"part:{pn}", f"variant:{a.variant_id}", "APPLICABLE_TO", a.applicability,
             meta={"applicability": a.applicability, "effectivity_from": a.effectivity_from, "effectivity_to": a.effectivity_to})
        part_domains[pn].add("configuration")

    # Immutable release baselines link only when every source document remains visible.
    baselines = db.scalars(select(ReleaseBaseline).where(ReleaseBaseline.project_code == project_code).order_by(ReleaseBaseline.frozen_at.desc())).all()
    for b in baselines[:12]:
        if not _area_ok(b.manufacturing_area, manufacturing_area, allowed):
            continue
        if not set(b.source_document_ids or []).issubset(visible_document_ids):
            continue
        bid = node("release", b.id, f"{b.code} · {b.name}", status="candidate" if b.release_candidate else "needs_review",
                   manufacturing_area=b.manufacturing_area,
                   meta={"baseline_type": b.baseline_type, "fingerprint": b.fingerprint, "frozen_at": b.frozen_at.isoformat(),
                         "release_candidate": b.release_candidate})
        for doc_id in b.source_document_ids or []:
            if f"document:{doc_id}" in nodes:
                edge(bid, f"document:{doc_id}", "SNAPSHOTS", "фиксирует")
                d = docs_by_id.get(doc_id)
                if d and d.part_number in visible_part_numbers:
                    part_domains[d.part_number].add("release")

    # Explicit document coverage gaps: a part is not "complete" just because one file exists.
    for pn in sorted(visible_part_numbers):
        kinds = doc_types_by_part.get(pn, set())
        if "drawing" not in kinds:
            gaps.append({"type": "document_trace", "severity": "warning", "part_number": pn, "title": f"{pn}: нет доступного актуального чертежа"})
        if "cad" not in kinds and "cad_native" not in kinds:
            gaps.append({"type": "document_trace", "severity": "warning", "part_number": pn, "title": f"{pn}: нет доступной 3D/CAD модели"})

    # Explainable cross-domain coverage. Only configured domains participate in the denominator.
    domain_order = ["documents", "product_structure", "requirements", "process", "quality", "supplier", "cost", "change", "architecture", "configuration", "release"]
    configured_domains = [d for d in domain_order if any(d in values for values in part_domains.values())]
    part_coverage = []
    for pn in sorted(visible_part_numbers):
        linked = sorted(part_domains[pn])
        pct = round(100.0 * len(set(linked) & set(configured_domains)) / max(len(configured_domains), 1), 1) if configured_domains else 0.0
        part_coverage.append({"part_number": pn, "coverage_pct": pct, "domains": linked, "missing_domains": [d for d in configured_domains if d not in linked]})
    coverage_pct = round(sum(x["coverage_pct"] for x in part_coverage) / max(len(part_coverage), 1), 1) if part_coverage else 0.0

    # Focused impact-thread is an undirected neighborhood for navigation only; edge direction remains preserved in output.
    full_nodes = nodes
    full_edges = edges
    focus_id = f"part:{focus}" if focus else None
    reachable: set[str]
    if focus_id:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for e in full_edges.values():
            adjacency[e["source"]].add(e["target"])
            adjacency[e["target"]].add(e["source"])
        reachable = {focus_id}
        q = deque([(focus_id, 0)])
        while q:
            current, level = q.popleft()
            if level >= depth:
                continue
            for nxt in adjacency.get(current, set()):
                if nxt not in reachable:
                    reachable.add(nxt); q.append((nxt, level + 1))
        selected_ids = list(reachable)
    else:
        # Stable ordering keeps high-value engineering objects when a very large project is truncated.
        priority = {"part": 0, "change": 1, "issue": 2, "requirement": 3, "operation": 4, "supplier": 5,
                    "architecture": 6, "interface": 7, "variant": 8, "cost": 9, "release": 10, "verification": 11, "document": 12}
        selected_ids = sorted(full_nodes, key=lambda nid: (priority.get(full_nodes[nid]["type"], 99), full_nodes[nid]["label"]))
    truncated = len(selected_ids) > max_nodes
    selected = set(selected_ids[:max_nodes])
    nodes_out = [full_nodes[nid] for nid in selected_ids if nid in selected]
    edges_out = [e for e in full_edges.values() if e["source"] in selected and e["target"] in selected]

    # Compact route explanations from focused part to representative domain nodes.
    routes = []
    if focus_id and focus_id in full_nodes:
        adjacency_edges: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for e in full_edges.values():
            adjacency_edges[e["source"]].append((e["target"], e))
            adjacency_edges[e["target"]].append((e["source"], e))
        target_types = {"requirement", "operation", "supplier", "cost", "change", "issue", "interface", "variant", "release"}
        found_types = set()
        q = deque([(focus_id, [focus_id], [])]); visited = {focus_id}
        while q and len(routes) < 10:
            current, path_nodes, path_edges = q.popleft()
            current_type = full_nodes[current]["type"]
            if current != focus_id and current_type in target_types and current_type not in found_types:
                found_types.add(current_type)
                routes.append({
                    "target_type": current_type,
                    "target_id": current,
                    "path": [{"id": x, "type": full_nodes[x]["type"], "label": full_nodes[x]["label"]} for x in path_nodes],
                    "relations": [x["relation"] for x in path_edges],
                })
            if len(path_edges) >= depth:
                continue
            for nxt, e in adjacency_edges.get(current, []):
                if nxt not in visited:
                    visited.add(nxt); q.append((nxt, path_nodes + [nxt], path_edges + [e]))

    type_counts: dict[str, int] = defaultdict(int)
    for n in nodes_out:
        type_counts[n["type"]] += 1
    critical_edges = sum(1 for e in edges_out if e.get("critical"))
    focus_coverage = next((x for x in part_coverage if x["part_number"] == focus), None) if focus else None

    return {
        "project_code": project_code,
        "manufacturing_area": manufacturing_area,
        "focus_part": focus,
        "depth": depth,
        "advisory_only": True,
        "deterministic_relationships_only": True,
        "human_release_approval_required": True,
        "plm_pdm_remains_product_structure_authority": True,
        "erp_remains_financial_transaction_authority": True,
        "summary": {
            "nodes": len(nodes_out),
            "edges": len(edges_out),
            "critical_edges": critical_edges,
            "gaps": len(gaps),
            "coverage_pct": focus_coverage["coverage_pct"] if focus_coverage else coverage_pct,
            "configured_domains": configured_domains,
            "type_counts": dict(sorted(type_counts.items())),
            "truncated": truncated,
        },
        "part_coverage": [x for x in part_coverage if not focus or x["part_number"] == focus],
        "gaps": [g for g in gaps if not focus or not g.get("part_number") or g.get("part_number") == focus][:80],
        "routes": routes,
        "nodes": nodes_out,
        "edges": edges_out,
        "legend": {
            "part": "Деталь / узел", "document": "Документ / CAD", "requirement": "Требование", "verification": "V&V",
            "operation": "Производственная операция", "supplier": "Поставщик / локализация", "cost": "Engineering Cost",
            "change": "ECR / ECO", "issue": "Замечание", "architecture": "Система / компонент", "interface": "Интерфейс",
            "variant": "Вариант автомобиля", "release": "Release baseline",
        },
    }
