import re


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 220) -> list[str]:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    sections = [p.strip() for p in re.split(r"\n{2,}|(?=^#{1,4}\s)", text, flags=re.M) if p.strip()]
    chunks: list[str] = []
    current = ""
    for section in sections:
        if len(current) + len(section) + 2 <= chunk_size:
            current = f"{current}\n\n{section}".strip()
            continue
        if current:
            chunks.append(current)
        if len(section) <= chunk_size:
            current = section
        else:
            start = 0
            while start < len(section):
                end = min(start + chunk_size, len(section))
                chunks.append(section[start:end])
                if end == len(section):
                    break
                start = max(end - overlap, start + 1)
            current = ""
    if current:
        chunks.append(current)
    return chunks
