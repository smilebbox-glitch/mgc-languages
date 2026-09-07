from pathlib import Path

from app.core.config import get_settings

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".json", ".xml"}


def parse_document(path: Path) -> tuple[str, dict]:
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        text = path.read_text(encoding="utf-8", errors="replace")
        return text, {"parser": "plain_text"}

    cfg = get_settings()
    from docling.document_converter import DocumentConverter

    if cfg.air_gapped_mode:
        artifacts = cfg.docling_artifacts_path
        if not artifacts.exists() or not artifacts.is_dir():
            raise RuntimeError(
                f"AIR_GAPPED_MODE requires local Docling artifacts at {artifacts}. "
                "Run scripts/prepare_models.py on the connected staging machine."
            )
        # Docling honors DOCLING_ARTIFACTS_PATH for local prefetched pipeline models.
        import os
        os.environ["DOCLING_ARTIFACTS_PATH"] = str(artifacts)

    converter = DocumentConverter()
    result = converter.convert(str(path))
    document = result.document
    text = document.export_to_markdown()
    meta = {"parser": "docling", "offline_artifacts": str(cfg.docling_artifacts_path) if cfg.air_gapped_mode else None}
    try:
        meta["page_count"] = len(document.pages)
    except Exception:
        pass
    return text, meta
