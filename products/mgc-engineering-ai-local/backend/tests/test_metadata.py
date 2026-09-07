from app.services.metadata import infer_metadata


def test_multilingual_metadata():
    text = """Part Number: 8450012345\nRevision: D\nMaterial: DP600\nThickness: 1.8 mm\nMass: 1.47 kg"""
    m = infer_metadata("drawing.pdf", text, ".pdf")
    assert m["part_number"] == "8450012345"
    assert m["revision"] == "D"
    assert m["material"] == "DP600"
    assert m["thickness_mm"] == 1.8
    assert m["mass_kg"] == 1.47


def test_russian_metadata():
    m = infer_metadata("8450099999_REV_C_spec.txt", "Материал: DP780\nТолщина: 2,0 мм", ".txt")
    assert m["part_number"] == "8450099999"
    assert m["revision"] == "C"
    assert m["material"] == "DP780"
    assert m["thickness_mm"] == 2.0
