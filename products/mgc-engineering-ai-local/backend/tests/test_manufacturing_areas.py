from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus, Part, Project, ProjectArea, ProjectMilestone
from app.db.session import Base
from app.services.manufacturing_areas import AREA_CATALOG, area_allowed, ensure_project_areas, infer_area_codes_from_groups
from app.services.project_workspace import project_workspace


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_default_automotive_areas_are_seeded_for_project():
    db = _db()
    project = Project(code="AUTO1", name="Vehicle Program", acl_groups=["engineering-ai-users"])
    db.add(project); db.commit()
    areas = ensure_project_areas(db, project)
    codes = {x.code for x in areas}
    assert len(areas) == len(AREA_CATALOG)
    assert {"assembly", "body_welding", "paint", "components", "logistics", "quality"} <= codes
    assert all(x.acl_groups == ["engineering-ai-users"] for x in areas)


def test_group_names_can_suggest_my_automotive_area_without_granting_access():
    assert "assembly" in infer_area_codes_from_groups(["plant-engineering-assembly"])
    assert "body_welding" in infer_area_codes_from_groups(["engineering-body-shop"])
    assert "paint" in infer_area_codes_from_groups(["paint-shop-engineers"])
    area = ProjectArea(project_code="P", code="assembly", name="Assembly", acl_groups=["eng-assembly"])
    assert area_allowed(area, ["eng-assembly"]) is True
    assert area_allowed(area, ["eng-paint"]) is False


def test_project_workspace_filters_parts_by_manufacturing_area_and_keeps_common_evidence():
    db = _db()
    project = Project(code="CAR", name="Car", root_part_number="ASSY", acl_groups=["engineering-ai-users"])
    db.add_all([project, Part(part_number="ASSY", project_code="CAR"), Part(part_number="WELD1", project_code="CAR"), Part(part_number="PAINT1", project_code="CAR")])
    docs = [
        Document(filename="weld.step", stored_path="/tmp/w", sha256="1"*64, status=DocumentStatus.ready, part_number="WELD1", revision="A", doc_type="cad", project_code="CAR", manufacturing_area="body_welding", acl_groups=["engineering-ai-users"]),
        Document(filename="weld.pdf", stored_path="/tmp/w2", sha256="2"*64, status=DocumentStatus.ready, part_number="WELD1", revision="A", doc_type="drawing", project_code="CAR", manufacturing_area=None, acl_groups=["engineering-ai-users"]),
        Document(filename="paint.pdf", stored_path="/tmp/p", sha256="3"*64, status=DocumentStatus.ready, part_number="PAINT1", revision="A", doc_type="drawing", project_code="CAR", manufacturing_area="paint", acl_groups=["engineering-ai-users"]),
        Document(filename="project_requirements.pdf", stored_path="/tmp/r", sha256="4"*64, status=DocumentStatus.ready, part_number=None, revision=None, doc_type="document", project_code="CAR", manufacturing_area=None, acl_groups=["engineering-ai-users"]),
    ]
    db.add_all(docs); db.commit()
    out = project_workspace(db, project, {d.id for d in docs}, manufacturing_area="body_welding", identity_groups=["engineering-ai-users"])
    assert {p["part_number"] for p in out["parts"]} == {"WELD1"}
    assert {d["filename"] for d in out["documents"]} == {"weld.step", "weld.pdf", "project_requirements.pdf"}
    assert out["manufacturing_area"] == "body_welding"
    assert any("Свар" in x or "соедин" in x for x in out["area_focus"])
    assert len(out["areas"]) == len(AREA_CATALOG)


def test_area_specific_milestones_are_filtered_but_common_milestones_remain():
    db = _db()
    project = Project(code="CAR2", name="Car2", acl_groups=["engineering-ai-users"])
    db.add(project)
    db.add_all([
        ProjectMilestone(project_code="CAR2", code="ALL", name="Design Release", manufacturing_area=None),
        ProjectMilestone(project_code="CAR2", code="WELD", name="Welding Fixture Ready", manufacturing_area="body_welding"),
        ProjectMilestone(project_code="CAR2", code="PAINT", name="Paint Trial", manufacturing_area="paint"),
    ])
    db.commit()
    out = project_workspace(db, project, set(), manufacturing_area="body_welding", identity_groups=["engineering-ai-users"])
    assert {m["code"] for m in out["milestones"]} == {"ALL", "WELD"}


def test_all_zones_workspace_respects_area_acl_for_documents_quality_process_and_milestones():
    from app.db.models import APQPDeliverable, ManufacturingLine

    db = _db()
    project = Project(code="ACL42", name="ACL Program", acl_groups=["engineering-ai-users"])
    db.add(project)
    db.add_all([
        ProjectArea(project_code="ACL42", code="assembly", name="Assembly", acl_groups=["engineering-ai-users"], sort_order=10),
        ProjectArea(project_code="ACL42", code="paint", name="Paint", acl_groups=["engineering-secret"], sort_order=20),
    ])
    db.add_all([
        Part(part_number="ASSY-P", project_code="ACL42"),
        Part(part_number="PAINT-P", project_code="ACL42"),
    ])
    assembly_doc = Document(
        filename="assembly.pdf", stored_path="/tmp/a", sha256="a" * 64, status=DocumentStatus.ready,
        part_number="ASSY-P", revision="A", doc_type="drawing", project_code="ACL42",
        manufacturing_area="assembly", acl_groups=["engineering-ai-users"],
    )
    paint_doc = Document(
        filename="paint-secret.pdf", stored_path="/tmp/p", sha256="b" * 64, status=DocumentStatus.ready,
        part_number="PAINT-P", revision="A", doc_type="drawing", project_code="ACL42",
        manufacturing_area="paint", acl_groups=["engineering-ai-users"],
    )
    common_doc = Document(
        filename="common.pdf", stored_path="/tmp/c", sha256="c" * 64, status=DocumentStatus.ready,
        part_number=None, revision=None, doc_type="document", project_code="ACL42",
        manufacturing_area=None, acl_groups=["engineering-ai-users"],
    )
    db.add_all([assembly_doc, paint_doc, common_doc])
    db.flush()
    db.add_all([
        ProjectMilestone(project_code="ACL42", code="ASSY", name="Assembly ready", manufacturing_area="assembly"),
        ProjectMilestone(project_code="ACL42", code="PAINT", name="Paint trial", manufacturing_area="paint"),
        APQPDeliverable(project_code="ACL42", manufacturing_area="assembly", code="A-APQP", phase="industrialization", title="Assembly APQP"),
        APQPDeliverable(project_code="ACL42", manufacturing_area="paint", code="P-APQP", phase="industrialization", title="Paint APQP"),
        ManufacturingLine(project_code="ACL42", manufacturing_area="assembly", code="AL1", name="Assembly line"),
        ManufacturingLine(project_code="ACL42", manufacturing_area="paint", code="PL1", name="Paint line"),
    ])
    db.commit()

    # The caller can see both document IDs at the document ACL layer, but is not in the Paint area ACL.
    # The project workspace must still filter Paint-area facts in the aggregate "All zones" view.
    out = project_workspace(
        db, project, {assembly_doc.id, paint_doc.id, common_doc.id}, manufacturing_area=None,
        identity_groups=["engineering-ai-users"],
    )

    assert {d["filename"] for d in out["documents"]} == {"assembly.pdf", "common.pdf"}
    assert {p["part_number"] for p in out["parts"]} == {"ASSY-P"}
    assert {m["code"] for m in out["milestones"]} == {"ASSY"}
    assert {x["code"] for x in out["quality"]["apqp"]} == {"A-APQP"}
    assert {x["code"] for x in out["process_thread"]["tree"]} == {"AL1"}
    assert "paint" not in {x["code"] for x in out["areas"]}
