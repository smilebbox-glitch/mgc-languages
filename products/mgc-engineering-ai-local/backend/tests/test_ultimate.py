from app.services.geometry_similarity import geometry_signature
from app.services.query_planner import plan_query


def test_agentic_revision_planner_does_not_parse_review_as_revision():
    p = plan_query("Проведи design review детали 8450012345 Rev C -> Rev D")
    assert p["intent"] == "design_review"
    assert p["part_number"] == "8450012345"
    assert p["baseline_revision"] == "C"
    assert p["revision"] == "D"
    assert p["revisions"] == ["C", "D"]


def test_geometry_signature_is_scale_invariant_for_bbox_ratios():
    a = geometry_signature({"bounding_box_mm":{"x":100,"y":60,"z":6},"volume_mm3":34000,"surface_area_mm2":14000,"face_count":11,"cylindrical_face_count":5})
    b = geometry_signature({"bounding_box_mm":{"x":200,"y":120,"z":12},"volume_mm3":272000,"surface_area_mm2":56000,"face_count":11,"cylindrical_face_count":5})
    assert a is not None and b is not None
    assert a[:3] == b[:3]


def test_query_planner_change_impact():
    p = plan_query("Оцени влияние изменения 8450012345 Rev C -> Rev D на сборки")
    assert p["intent"] == "change_impact"
    assert p["baseline_revision"] == "C"
    assert p["revision"] == "D"


def _db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.session import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_change_impact_propagates_to_parent_assembly():
    from app.db.models import BOMItem, Document, DocumentStatus, PartRevision
    from app.services.change_impact import analyze_change_impact
    db = _db_session()
    db.add_all([
        PartRevision(part_number="8450012345", revision="C", metadata_json={"volume_mm3":100.0}, document_ids=[]),
        PartRevision(part_number="8450012345", revision="D", metadata_json={"volume_mm3":120.0}, document_ids=[]),
        Document(filename="x.step", stored_path="/tmp/x", sha256="a"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="cad", acl_groups=["all"]),
        BOMItem(parent_part_number="ASM-100", parent_revision="A", child_part_number="8450012345", quantity=2, source_document_id="bom-doc"),
    ])
    db.commit()
    result = analyze_change_impact(db, "8450012345", "C", "D")
    assert any(x["part_number"] == "ASM-100" and x["reason"] == "parent_assembly" for x in result["impacted_parts"])
    assert result["risk_score"] > 0


def test_evidence_pack_contains_integrity_manifest():
    from app.db.models import Document, DocumentStatus
    from app.services.evidence_pack import build_evidence_pack
    db = _db_session()
    doc = Document(filename="spec.pdf", stored_path="/tmp/spec.pdf", sha256="b"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="spec", acl_groups=["all"])
    db.add(doc); db.commit()
    pack = build_evidence_pack(db, "8450012345", "D", "tester", "niokr")
    assert pack.manifest["integrity"]["all_sha256_present"] is True
    assert pack.manifest["documents"][0]["sha256"] == "b"*64


def test_design_review_flags_missing_evidence():
    from app.db.models import Document, DocumentStatus, PartRevision
    from app.services.design_review import run_design_review
    db = _db_session()
    db.add(PartRevision(part_number="8450012345", revision="D", metadata_json={"volume_mm3":120.0}, document_ids=[]))
    db.add(Document(filename="part.step", stored_path="/tmp/part.step", sha256="c"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="cad", acl_groups=["all"], extracted_metadata={"volume_mm3":120.0}))
    db.commit()
    review = run_design_review(db, "8450012345", "D", None, "tester")
    codes = {x["code"] for x in review.findings}
    assert "MISSING_DRAWING" in codes
    assert "MISSING_BOM" in codes
    assert review.risk_score > 0


def test_evidence_pack_acl_excludes_hidden_document():
    from app.db.models import Document, DocumentStatus
    from app.services.evidence_pack import build_evidence_pack
    db = _db_session()
    visible = Document(filename="visible.pdf", stored_path="/tmp/v.pdf", sha256="d"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="drawing", acl_groups=["team-a"])
    hidden = Document(filename="hidden.pdf", stored_path="/tmp/h.pdf", sha256="e"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="requirement", acl_groups=["secret"])
    db.add_all([visible, hidden]); db.commit()
    pack = build_evidence_pack(db, "8450012345", "D", "tester", allowed_document_ids={visible.id})
    assert [x["id"] for x in pack.manifest["documents"]] == [visible.id]


def test_revision_compare_acl_does_not_use_hidden_metadata():
    from app.db.models import Document, DocumentStatus, PartRevision
    from app.services.revision_compare import compare_revisions
    db = _db_session()
    c = Document(filename="c.step", stored_path="/tmp/c", sha256="f"*64, status=DocumentStatus.ready, part_number="8450012345", revision="C", doc_type="cad", acl_groups=["team"], extracted_metadata={"volume_mm3":100.0})
    d = Document(filename="d.step", stored_path="/tmp/d", sha256="1"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="cad", acl_groups=["team"], extracted_metadata={"volume_mm3":120.0})
    secret = Document(filename="secret.txt", stored_path="/tmp/s", sha256="2"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="requirement", acl_groups=["secret"], extracted_metadata={"material":"SECRET-ALLOY"})
    db.add_all([c,d,secret, PartRevision(part_number="8450012345", revision="C", metadata_json={"volume_mm3":100.0}, document_ids=[]), PartRevision(part_number="8450012345", revision="D", metadata_json={"volume_mm3":120.0,"material":"SECRET-ALLOY"}, document_ids=[])])
    db.commit()
    result = compare_revisions(db, "8450012345", "C", "D", {c.id,d.id})
    fields = {x["field"] for x in result["metadata_changes"]}
    assert "volume_mm3" in fields
    assert "material" not in fields


def test_change_impact_acl_does_not_traverse_hidden_bom():
    from app.db.models import BOMItem, Document, DocumentStatus, PartRevision
    from app.services.change_impact import analyze_change_impact
    db = _db_session()
    visible = Document(filename="d.step", stored_path="/tmp/d", sha256="3"*64, status=DocumentStatus.ready, part_number="8450012345", revision="D", doc_type="cad", acl_groups=["team"])
    hidden_bom = Document(filename="secret_bom.csv", stored_path="/tmp/b", sha256="4"*64, status=DocumentStatus.ready, part_number="SECRET-ASM", revision="A", doc_type="bom", acl_groups=["secret"])
    db.add_all([visible, hidden_bom, PartRevision(part_number="8450012345", revision="C", metadata_json={}, document_ids=[]), PartRevision(part_number="8450012345", revision="D", metadata_json={}, document_ids=[])])
    db.commit()
    db.add(BOMItem(parent_part_number="SECRET-ASM", parent_revision="A", child_part_number="8450012345", quantity=1, source_document_id=hidden_bom.id)); db.commit()
    result = analyze_change_impact(db, "8450012345", "C", "D", allowed_document_ids={visible.id})
    assert not any(x["part_number"] == "SECRET-ASM" for x in result["impacted_parts"])
