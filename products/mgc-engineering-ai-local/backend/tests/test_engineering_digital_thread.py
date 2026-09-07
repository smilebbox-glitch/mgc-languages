from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    ArchitectureNode,
    BOMItem,
    ChangeRequest,
    ConfigurationApplicability,
    CostBaseline,
    CostLine,
    Document,
    DocumentStatus,
    EngineeringRequirement,
    InterfaceDefinition,
    LocalizationItem,
    ManufacturingLine,
    Part,
    ProcessOperation,
    ProcessStation,
    Project,
    ReleaseBaseline,
    RequirementVerification,
    ValidationIssue,
    VehicleVariant,
    IssueSeverity,
    IssueStatus,
)
from app.db.session import Base
from app.services.engineering_digital_thread import engineering_digital_thread
from app.services.change_intelligence import change_intelligence_workspace, simulate_change_impact, compare_digital_thread_baselines


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code: str = "DT1"):
    project = Project(code=code, name="Digital Thread Pilot", root_part_number="ASSY-1", acl_groups=["engineering-ai-users"])
    assy = Part(part_number="ASSY-1", name="Front module", project_code=code, latest_revision="B")
    child = Part(part_number="PART-1", name="Bracket", project_code=code, latest_revision="A")
    drawing = Document(
        filename="PART-1_A.pdf", stored_path="/tmp/part.pdf", sha256="a" * 64,
        status=DocumentStatus.ready, part_number="PART-1", revision="A", doc_type="drawing",
        project_code=code, manufacturing_area="assembly", acl_groups=["engineering-ai-users"],
    )
    cad = Document(
        filename="PART-1_A.step", stored_path="/tmp/part.step", sha256="b" * 64,
        status=DocumentStatus.ready, part_number="PART-1", revision="A", doc_type="cad",
        project_code=code, manufacturing_area="assembly", acl_groups=["engineering-ai-users"],
    )
    bom_doc = Document(
        filename="ASSY-1_BOM.xlsx", stored_path="/tmp/bom.xlsx", sha256="c" * 64,
        status=DocumentStatus.ready, part_number="ASSY-1", revision="B", doc_type="bom",
        project_code=code, manufacturing_area="assembly", acl_groups=["engineering-ai-users"],
    )
    wi = Document(
        filename="WI-ASM-10.pdf", stored_path="/tmp/wi.pdf", sha256="d" * 64,
        status=DocumentStatus.ready, part_number="PART-1", revision="1", doc_type="work_instruction",
        project_code=code, manufacturing_area="assembly", acl_groups=["engineering-ai-users"],
    )
    db.add_all([project, assy, child, drawing, cad, bom_doc, wi]); db.commit()
    for row in [drawing, cad, bom_doc, wi]: db.refresh(row)

    db.add(BOMItem(parent_part_number="ASSY-1", parent_revision="B", child_part_number="PART-1", child_revision="A", quantity=2, position="110", source_document_id=bom_doc.id))

    req = EngineeringRequirement(
        project_code=code, manufacturing_area="assembly", code="REQ-001", title="Bracket strength",
        requirement_text="Bracket shall withstand target load", source_document_id=drawing.id,
        part_numbers=["PART-1"], criticality="critical", verification_method="test",
    )
    db.add(req); db.commit(); db.refresh(req)
    ver = RequirementVerification(
        project_code=code, requirement_id=req.id, manufacturing_area="assembly", code="VV-001",
        title="Static load test", status="passed", evidence_document_ids=[drawing.id],
    )
    db.add(ver)

    line = ManufacturingLine(project_code=code, manufacturing_area="assembly", code="ASM-1", name="Assembly line")
    db.add(line); db.commit(); db.refresh(line)
    station = ProcessStation(line_id=line.id, code="ST-10", name="Install bracket")
    db.add(station); db.commit(); db.refresh(station)
    db.add(ProcessOperation(station_id=station.id, code="OP-10", name="Install", part_number="PART-1", operation_type="assembly", work_instruction_document_ids=[wi.id]))

    db.add(LocalizationItem(project_code=code, manufacturing_area="assembly", part_number="PART-1", supplier_code="SUP-1", supplier_name="Local Supplier", status="ppap", localization_percent=75, evidence_document_ids=[drawing.id]))
    cost = CostBaseline(project_code=code, manufacturing_area="assembly", code="CUR-26", name="Current", baseline_type="current", status="active", currency="RUB")
    db.add(cost); db.commit(); db.refresh(cost)
    db.add(CostLine(project_code=code, baseline_id=cost.id, manufacturing_area="assembly", part_number="PART-1", calculation_mode="quote", supplier_unit_price=1250, evidence_document_ids=[drawing.id]))
    db.add(ChangeRequest(code=f"ECR-{code}", title="Increase bracket stiffness", part_number="PART-1", from_revision="A", to_revision="B", status="impact_review", risk_level="high"))
    db.add(ValidationIssue(part_number="PART-1", revision="A", severity=IssueSeverity.warning, status=IssueStatus.open, rule_code="TEST_GAP", title="Review tolerance", document_ids=[drawing.id], fingerprint=("f" * 60 + code)[-64:]))

    a1 = ArchitectureNode(project_code=code, manufacturing_area="assembly", code="BRACKET", name="Bracket component", node_type="component", part_number="PART-1", evidence_document_ids=[drawing.id])
    a2 = ArchitectureNode(project_code=code, manufacturing_area="assembly", code="BODY", name="Body interface", node_type="assembly", evidence_document_ids=[drawing.id])
    db.add_all([a1, a2]); db.commit(); db.refresh(a1); db.refresh(a2)
    db.add(InterfaceDefinition(project_code=code, manufacturing_area="assembly", code="IF-001", name="Bracket to body", interface_type="mechanical", source_node_id=a1.id, target_node_id=a2.id, criticality="high", requirement_ids=[req.id], evidence_document_ids=[drawing.id]))

    variant = VehicleVariant(project_code=code, manufacturing_area="assembly", code="V1", name="Base", model_year="2027", evidence_document_ids=[drawing.id])
    db.add(variant); db.commit(); db.refresh(variant)
    db.add(ConfigurationApplicability(project_code=code, variant_id=variant.id, manufacturing_area="assembly", entity_type="part", entity_key="PART-1", applicability="included", evidence_document_ids=[drawing.id]))
    db.add(ReleaseBaseline(project_code=code, manufacturing_area="assembly", code="DF-01", name="Design Freeze", baseline_type="design_freeze", fingerprint="e" * 64, source_document_ids=[drawing.id, cad.id, bom_doc.id, wi.id], release_candidate=True))
    db.commit()
    return {"project": project, "docs": [drawing, cad, bom_doc, wi], "part_numbers": {"ASSY-1", "PART-1"}}


def test_digital_thread_connects_major_engineering_domains():
    db = _db(); seed = _seed(db)
    visible = {d.id for d in seed["docs"]}
    out = engineering_digital_thread(db, seed["project"].code, visible, seed["part_numbers"], "assembly", {"assembly"})
    types = {n["type"] for n in out["nodes"]}
    assert {"part", "document", "requirement", "verification", "operation", "supplier", "cost", "change", "issue", "architecture", "interface", "variant", "release"}.issubset(types)
    relations = {e["relation"] for e in out["edges"]}
    assert {"BOM_CONTAINS", "HAS_REQUIREMENT", "VERIFIED_BY", "MANUFACTURED_BY", "SUPPLIES", "HAS_COST", "CHANGED_BY", "HAS_ISSUE", "REPRESENTED_BY", "APPLICABLE_TO", "SNAPSHOTS"}.issubset(relations)
    assert out["deterministic_relationships_only"] is True
    assert out["human_release_approval_required"] is True
    assert out["summary"]["coverage_pct"] > 0


def test_focus_mode_returns_local_impact_thread_and_routes():
    db = _db(); seed = _seed(db, "DT2")
    visible = {d.id for d in seed["docs"]}
    out = engineering_digital_thread(db, seed["project"].code, visible, seed["part_numbers"], "assembly", {"assembly"}, focus_part="part-1", depth=2)
    ids = {n["id"] for n in out["nodes"]}
    assert "part:PART-1" in ids
    assert out["focus_part"] == "PART-1"
    assert out["depth"] == 2
    assert any(r["target_type"] in {"requirement", "operation", "supplier", "cost", "change", "issue", "variant"} for r in out["routes"])
    assert all(x["part_number"] == "PART-1" for x in out["part_coverage"])


def test_hidden_evidence_fails_closed_across_thread():
    db = _db(); seed = _seed(db, "DT3")
    hidden = Document(
        filename="secret-supplier.pdf", stored_path="/tmp/secret", sha256="9" * 64,
        status=DocumentStatus.ready, part_number="PART-1", revision="A", doc_type="spec",
        project_code=seed["project"].code, manufacturing_area="assembly", acl_groups=["secret-group"],
    )
    db.add(hidden); db.commit(); db.refresh(hidden)
    db.add(LocalizationItem(project_code=seed["project"].code, manufacturing_area="assembly", part_number="PART-1", supplier_code="SUP-SECRET", supplier_name="Secret Supplier", status="candidate", evidence_document_ids=[hidden.id]))
    db.add(ArchitectureNode(project_code=seed["project"].code, manufacturing_area="assembly", code="SECRET-NODE", name="Secret architecture", node_type="component", part_number="PART-1", evidence_document_ids=[hidden.id]))
    hidden_cost = CostBaseline(project_code=seed["project"].code, manufacturing_area="assembly", code="SECRET-COST", name="Secret cost", baseline_type="scenario", currency="RUB", evidence_document_ids=[hidden.id])
    db.add(hidden_cost); db.commit(); db.refresh(hidden_cost)
    db.add(CostLine(project_code=seed["project"].code, baseline_id=hidden_cost.id, manufacturing_area="assembly", part_number="PART-1", calculation_mode="quote", supplier_unit_price=9999))
    db.add(ChangeRequest(code=f"ECR-SECRET-{seed['project'].code}", title="Secret change", part_number="PART-1", status="draft", affected_document_ids=[hidden.id]))
    db.add(ValidationIssue(part_number="PART-1", revision="A", severity=IssueSeverity.warning, status=IssueStatus.open, rule_code="SECRET", title="Secret validation issue", document_ids=[seed["docs"][0].id, hidden.id], fingerprint=("1" * 60 + seed["project"].code)[-64:]))
    db.commit()
    visible = {d.id for d in seed["docs"]}
    out = engineering_digital_thread(db, seed["project"].code, visible, seed["part_numbers"], "assembly", {"assembly"})
    labels = {n["label"] for n in out["nodes"]}
    assert not any("Secret Supplier" in x for x in labels)
    assert not any("Secret architecture" in x for x in labels)
    assert not any("Secret cost" in x for x in labels)
    assert not any("Secret change" in x for x in labels)
    assert not any("Secret validation issue" in x for x in labels)
    assert not any(n["id"] == f"document:{hidden.id}" for n in out["nodes"])


def test_unknown_focus_part_is_not_leaked():
    db = _db(); seed = _seed(db, "DT4")
    visible = {d.id for d in seed["docs"]}
    try:
        engineering_digital_thread(db, seed["project"].code, visible, seed["part_numbers"], "assembly", {"assembly"}, focus_part="SECRET-PART")
        assert False, "expected LookupError"
    except LookupError as exc:
        assert str(exc) == "Part not found"



def test_v51_change_intelligence_workspace_has_queue_coverage_variants_and_freshness():
    db = _db(); seed = _seed(db, "CI51A")
    visible = {d.id for d in seed["docs"]}
    out = change_intelligence_workspace(db, seed["project"].code, visible, seed["part_numbers"], "assembly", {"assembly"})
    assert out["coverage"]["score"] >= 0
    assert out["variant_matrix"]["variants"][0]["code"] == "V1"
    assert any(r["part_number"] == "PART-1" for r in out["variant_matrix"]["rows"])
    assert out["counts"]["actions"] > 0
    assert any(x["state"] in {"CURRENT", "REVIEW_REQUIRED", "MISSING", "STALE", "UNKNOWN"} for x in out["stale_evidence"])
    assert out["advisory_only"] is True


def test_v51_change_impact_simulator_returns_cross_domain_actions_routes_and_workshop():
    db = _db(); seed = _seed(db, "CI51B")
    visible = {d.id for d in seed["docs"]}
    scenario = {
        "part_number": "PART-1", "from_revision": "A", "to_revision": "B",
        "material_from": "DC01", "material_to": "DP600",
        "thickness_from_mm": 1.2, "thickness_to_mm": 1.5,
        "supplier_from": "SUP-1", "supplier_to": "SUP-2",
        "unit_cost_from": 1250, "unit_cost_to": 1180, "annual_volume": 10000,
        "quantity_per_vehicle": 1.0, "currency": "RUB", "geometry_changed": True,
    }
    out = simulate_change_impact(db, seed["project"].code, visible, seed["part_numbers"], scenario, "assembly", {"assembly"})
    keys = {x["key"] for x in out["categories"]}
    assert {"product", "design", "validation", "manufacturing", "supplier", "cost", "release"}.issubset(keys)
    assert any(x["state"] == "STALE" for x in out["stale_evidence"])
    assert any("PPAP" in x["action"] for x in out["actions"])
    assert out["workshop_impact"][0]["manufacturing_area"] == "assembly"
    assert out["cost_impact"]["unit_delta"] == -70.0
    assert out["cost_impact"]["annual_delta"] == -700000.0
    assert out["simulation_only"] is True
    assert out["does_not_modify_engineering_records"] is True


def test_v51_simulator_rejects_empty_scenario_and_unknown_part_without_leak():
    db = _db(); seed = _seed(db, "CI51C")
    visible = {d.id for d in seed["docs"]}
    try:
        simulate_change_impact(db, seed["project"].code, visible, seed["part_numbers"], {"part_number": "PART-1"}, "assembly", {"assembly"})
        assert False, "empty scenario must fail"
    except ValueError as exc:
        assert "material engineering change" in str(exc)
    try:
        simulate_change_impact(db, seed["project"].code, visible, seed["part_numbers"], {"part_number": "SECRET", "from_revision": "A", "to_revision": "B"}, "assembly", {"assembly"})
        assert False, "unknown part must fail"
    except LookupError as exc:
        assert str(exc) == "Part not found"


def test_v51_full_digital_thread_baseline_diff_covers_process_cost_and_readiness():
    db = _db(); seed = _seed(db, "CI51D")
    visible = {d.id for d in seed["docs"]}
    left = ReleaseBaseline(
        project_code=seed["project"].code, code="DF-L", name="Left", baseline_type="design_freeze",
        fingerprint="1"*64, source_document_ids=list(visible), release_candidate=True,
        snapshot_json={
            "schema":"mgc-release-baseline-v2", "documents":[], "bom":[], "requirements":[], "verifications":[],
            "suppliers":[], "ppap":[], "changes":[], "critical_issues":[], "part_revisions":[],
            "configuration":{"included_parts":[],"excluded_parts":[],"unknown_parts":[],"unknown_document_ids":[]},
            "process_operations":[{"part_number":"PART-1","line":"ASM-1","station":"ST-10","code":"OP-10","cycle_time_sec":20}],
            "cost_lines":[{"part_number":"PART-1","baseline_code":"CUR","supplier_code":"SUP-1","supplier_unit_price":1250}],
            "architecture_nodes":[{"code":"BRACKET","status":"active"}], "interfaces":[],
        },
    )
    right = ReleaseBaseline(
        project_code=seed["project"].code, code="DF-R", name="Right", baseline_type="design_freeze",
        fingerprint="2"*64, source_document_ids=list(visible), release_candidate=True,
        snapshot_json={
            "schema":"mgc-release-baseline-v2", "documents":[], "bom":[], "requirements":[], "verifications":[],
            "suppliers":[], "ppap":[], "changes":[], "critical_issues":[], "part_revisions":[],
            "configuration":{"included_parts":[],"excluded_parts":[],"unknown_parts":[],"unknown_document_ids":[]},
            "process_operations":[{"part_number":"PART-1","line":"ASM-1","station":"ST-10","code":"OP-10","cycle_time_sec":24}],
            "cost_lines":[{"part_number":"PART-1","baseline_code":"CUR","supplier_code":"SUP-1","supplier_unit_price":1180}],
            "architecture_nodes":[{"code":"BRACKET","status":"changed"}], "interfaces":[],
        },
    )
    db.add_all([left,right]); db.commit(); db.refresh(left); db.refresh(right)
    out = compare_digital_thread_baselines(left,right)
    assert out["process"]["summary"]["changed"] == 1
    assert out["cost"]["summary"]["changed"] == 1
    assert out["architecture"]["summary"]["changed"] == 1
    assert out["readiness"]["advisory_only"] is True
    assert out["full_digital_thread_diff"] is True
