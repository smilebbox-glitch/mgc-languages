from app.services.geometry_linking import link_entities_to_geometry


def test_unique_diameter_links_to_brep_face():
    drawing = {"entities": [{
        "type": "diameter", "raw": "Ø12 ±0.1", "nominal": 12.0,
        "upper_tolerance": 0.1, "lower_tolerance": -0.1,
        "page": 1, "bbox": [10, 20, 50, 32], "source_method": "vector_text",
    }]}
    cad = {"geometry_features": [
        {"feature_id": "face:0007", "kind": "cylindrical_face", "diameter_mm": 12.0, "radius_mm": 6.0},
        {"feature_id": "face:0008", "kind": "cylindrical_face", "diameter_mm": 8.0, "radius_mm": 4.0},
    ], "bounding_box_mm": {"x": 100, "y": 60, "z": 6}}
    result = link_entities_to_geometry(drawing, cad)
    assert result["linked_unique"] == 1
    assert result["links"][0]["verified"] is True
    assert result["links"][0]["candidates"][0]["feature_id"] == "face:0007"


def test_repeated_equal_features_stay_ambiguous():
    drawing = {"entities": [{"type": "diameter", "raw": "Ø8", "nominal": 8.0, "page": 1, "bbox": [1, 2, 3, 4]}]}
    cad = {"geometry_features": [
        {"feature_id": "face:0001", "kind": "cylindrical_face", "diameter_mm": 8.0, "radius_mm": 4.0},
        {"feature_id": "face:0002", "kind": "cylindrical_face", "diameter_mm": 8.0, "radius_mm": 4.0},
    ]}
    result = link_entities_to_geometry(drawing, cad)
    link = result["links"][0]
    assert link["status"] == "linked_multiple"
    assert link["candidate_count"] == 2
    assert link["verified"] is False


def test_thickness_can_link_to_thin_part_extent():
    drawing = {"entities": [{"type": "thickness", "raw": "THK 1.5", "value": 1.5, "page": 1, "bbox": [1, 2, 3, 4]}]}
    cad = {
        "geometry_features": [],
        "bounding_box_mm": {"x": 100, "y": 40, "z": 1.5},
        "thin_part_candidate": True,
        "bbox_min_thickness_candidate_mm": 1.5,
    }
    result = link_entities_to_geometry(drawing, cad)
    assert result["links"][0]["status"] == "linked_unique"
    assert result["links"][0]["candidates"][0]["feature_id"] == "shape:thin-thickness"


def test_release_demo_shows_unique_ambiguous_and_thickness(tmp_path):
    from pathlib import Path
    from app.services.cad import analyze_step
    from app.services.drawing_intelligence import analyze_drawing

    root = Path(__file__).resolve().parents[2]
    drawing = analyze_drawing(root / "samples" / "8450012345_REV_D_geometry_link_demo.pdf", "")
    _, cad, _ = analyze_step(root / "samples" / "8450012345_REV_D_mounting_plate.step", tmp_path)
    result = link_entities_to_geometry(drawing, cad)
    assert result["linked_unique"] == 2
    assert result["linked_multiple"] == 1
    assert result["unmatched"] == 0


def test_inch_dimension_is_normalized_to_mm():
    drawing = {"entities": [{"type": "diameter", "raw": 'Ø0.5"', "nominal": 0.5, "unit": '"', "page": 1, "bbox": [1,2,3,4]}]}
    cad = {"geometry_features": [{"feature_id": "face:0010", "kind": "cylindrical_face", "diameter_mm": 12.7, "radius_mm": 6.35}]}
    result = link_entities_to_geometry(drawing, cad)
    assert result["links"][0]["status"] == "linked_unique"
    assert result["links"][0]["candidates"][0]["drawing_value_mm"] == 12.7
