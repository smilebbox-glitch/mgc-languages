from pathlib import Path

from app.services.cad import analyze_step


def test_demo_step_revision_d(tmp_path: Path):
    sample = Path(__file__).resolve().parents[2] / "samples" / "8450012345_REV_D_mounting_plate.step"
    if not sample.exists():
        return
    _, meta, preview = analyze_step(sample, tmp_path)
    assert meta["solid_count"] == 1
    assert round(meta["bounding_box_mm"]["x"], 3) == 100.0
    assert meta["cylindrical_face_count"] >= 5
    assert 12.0 in meta["cylindrical_diameters_mm"]
    assert any(x.get("feature_id") == "face:0009" and x.get("diameter_mm") == 12.0 for x in meta["geometry_features"])
    assert preview and preview.exists()
