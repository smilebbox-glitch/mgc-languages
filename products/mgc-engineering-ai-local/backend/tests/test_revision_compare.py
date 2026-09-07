from app.services.revision_compare import _delta


def test_numeric_delta():
    d = _delta(100.0, 110.0)
    assert d["delta"] == 10.0
    assert round(d["percent"], 2) == 10.0
