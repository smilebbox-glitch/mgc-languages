from pathlib import Path

import pytest

from app.services.drawing_vision import build_consensus
from app.services.engineering_entities import parse_engineering_entities
from app.services.geometry_similarity import geometry_signature, explain_similarity
from app.services.step_semantics import inspect_step_semantics


def test_engineering_entity_parser_is_conservative_and_structured():
    text = "Ø25 ±0.1 mm | M10x1.25 6H | Ra 1.6 | THK: 1.5 mm | DATUM A | ISO 2768-mK"
    rows = parse_engineering_entities(text, page=1, bbox=[10, 20, 200, 40], source_method="vector_text", confidence=0.97)
    by_type = {}
    for row in rows:
        by_type.setdefault(row["type"], []).append(row)
    dia = by_type["diameter"][0]
    assert dia["nominal"] == 25.0
    assert dia["upper_tolerance"] == 0.1
    assert dia["lower_tolerance"] == -0.1
    assert dia["bbox"] == [10.0, 20.0, 200.0, 40.0]
    assert by_type["thread"][0]["designation"].startswith("M10X1.25")
    assert by_type["surface_finish"][0]["value_um"] == 1.6
    assert by_type["thickness"][0]["value"] == 1.5
    assert by_type["datum"][0]["datum"] == "A"


def test_vector_pdf_extracts_title_block_and_bbox(tmp_path: Path):
    fitz = pytest.importorskip("fitz")
    from app.services.vector_drawing import analyze_vector_pdf

    path = tmp_path / "drawing.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(320, 660, 580, 825))
    page.insert_text((330, 690), "PART NUMBER: 8450012345")
    page.insert_text((330, 715), "REV: D")
    page.insert_text((330, 740), "MATERIAL: SUS409L")
    page.insert_text((330, 765), "THK: 1.5 mm")
    page.insert_text((80, 200), "Ø25 ±0.1 mm")
    doc.save(str(path))
    doc.close()

    text, meta = analyze_vector_pdf(path)
    assert "8450012345" in text
    assert meta["content_layer"] in {"vector", "text"}
    assert meta["title_block"]["part_number"]["value"] == "8450012345"
    assert meta["title_block"]["revision"]["value"] == "D"
    assert meta["title_block"]["material"]["value"] == "SUS409L"
    assert any(x["type"] == "diameter" and x.get("bbox") for x in meta["entities"])
    assert meta["provenance"]["authoritative_for_text_positions"] is True


def test_step_semantics_detects_ap242_and_pmi_signals(tmp_path: Path):
    p = tmp_path / "part.step"
    p.write_text("""ISO-10303-21;
HEADER;
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('1','MOUNTING BRACKET','',());
#2=GEOMETRIC_TOLERANCE('x','',#3,#4);
#3=DATUM_FEATURE('A','',#4);
#4=DIMENSIONAL_SIZE(#5,'DIA');
ENDSEC;
END-ISO-10303-21;
""", encoding="latin-1")
    meta = inspect_step_semantics(p)
    assert meta["ap242_detected"] is True
    assert meta["pmi_semantics_present"] is True
    assert meta["pmi_values_decoded"] is False
    assert meta["pmi_semantic_signal_count"] >= 3


def test_vlm_consensus_never_replaces_deterministic_entity():
    deterministic = [{"type": "diameter", "nominal": 25.0, "raw": "Ø25", "page": 1, "confidence": 0.97}]
    pages = [{"page_number": 1, "structured": {"entities": [{"type": "diameter", "value": 25.0, "raw": "Ø25", "confidence": 0.91}]}}]
    result = build_consensus(deterministic, pages)
    assert len(result["confirmed"]) == 1
    assert result["confirmed"][0]["deterministic"]["nominal"] == 25.0
    assert "authoritative" in result["policy"].lower()


def test_geometry_signature_v2_explains_similarity():
    a = geometry_signature({
        "bounding_box_mm": {"x": 100, "y": 60, "z": 6}, "volume_mm3": 34000,
        "surface_area_mm2": 14000, "face_count": 20, "edge_count": 40,
        "cylindrical_face_count": 4, "planar_face_count": 16,
        "cylindrical_radii_mm": [4, 4], "compactness": 0.18,
    })
    b = geometry_signature({
        "bounding_box_mm": {"x": 102, "y": 60, "z": 6}, "volume_mm3": 35000,
        "surface_area_mm2": 14200, "face_count": 20, "edge_count": 40,
        "cylindrical_face_count": 4, "planar_face_count": 16,
        "cylindrical_radii_mm": [4, 4], "compactness": 0.18,
    })
    assert a and b
    factors = explain_similarity(a, b)
    assert factors["bbox_shape"] > 0.95
    assert factors["topology"] == 1.0


def _vision_db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.session import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_validation_flags_ambiguous_drawing_thickness():
    from app.db.models import Document, DocumentStatus
    from app.services.validation import validate_part
    db = _vision_db_session()
    doc = Document(
        filename="bracket_drawing.pdf", stored_path="/tmp/bracket_drawing.pdf", sha256="9" * 64,
        status=DocumentStatus.ready, part_number="BRACKET-001", revision="A", doc_type="drawing", acl_groups=["all"],
        extracted_metadata={"engineering_drawing": {
            "entities": [{"type": "thickness", "value": 1.2}, {"type": "thickness", "value": 1.5}],
            "normalized_facts": {"thickness_candidates_mm": [1.2, 1.5], "thickness_conflict": True},
            "provenance": {"coordinate_evidence_available": True, "methods": ["pymupdf_vector"]},
        }},
    )
    db.add(doc); db.commit()
    issues = validate_part(db, "BRACKET-001")
    assert "DRAWING_THICKNESS_AMBIGUOUS" in {x.rule_code for x in issues}


def test_validation_flags_drawing_facts_without_coordinate_evidence():
    from app.db.models import Document, DocumentStatus
    from app.services.validation import validate_part
    db = _vision_db_session()
    doc = Document(
        filename="scan.png", stored_path="/tmp/scan.png", sha256="8" * 64,
        status=DocumentStatus.ready, part_number="SCAN-001", revision="A", doc_type="drawing", acl_groups=["all"],
        extracted_metadata={"engineering_drawing": {
            "entities": [{"type": "diameter", "nominal": 25.0, "source_method": "docling_or_ocr_text"}],
            "normalized_facts": {"thickness_conflict": False},
            "provenance": {"coordinate_evidence_available": False, "methods": ["docling_or_ocr_text"]},
        }},
    )
    db.add(doc); db.commit()
    issues = validate_part(db, "SCAN-001")
    assert "DRAWING_REVIEW_REQUIRED" in {x.rule_code for x in issues}
