from app.services.chunking import chunk_text


def test_chunking_preserves_content():
    text = "A" * 900 + "\n\n" + "B" * 900
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    assert len(chunks) >= 2
    assert any("A" in x for x in chunks)
    assert any("B" in x for x in chunks)
