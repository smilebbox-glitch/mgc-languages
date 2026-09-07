from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, DocumentStatus
from app.services.bom import ingest_bom_csv
from app.services.cad import CAD_EXTENSIONS, STEP_EXTENSIONS, MESH_EXTENSIONS, DXF_EXTENSIONS, analyze_step, analyze_stl, analyze_dxf
from app.services.chunking import chunk_text
from app.services.document_parser import parse_document
from app.services.drawing_intelligence import analyze_drawing
from app.services.knowledge import register_document
from app.services.metadata import infer_metadata
from app.services.native_cad import native_cad_metadata
from app.services.projection_outbox import persist_document_chunks, enqueue_document_projections


def ingest_document(
    db: Session,
    doc: Document,
    *,
    correlation_id: str | None = None,
) -> Document:
    path = Path(doc.stored_path)
    cfg = get_settings()
    doc.status = DocumentStatus.processing; doc.error = None; db.commit()
    try:
        if doc.extension in cfg.proprietary_cad_extension_set:
            native_meta = native_cad_metadata(doc.extension)
            product = native_meta.get("product") or "Native CAD"
            text = f"{product} controlled source asset: {doc.filename}. Local gateway conversion is required for deterministic analysis."
            extracted = {
                "native_cad": True,
                "conversion_required": True,
                "source_format": doc.extension.lstrip("."),
                **native_meta,
            }
            preview = None
            doc.doc_type = "cad_native"
        elif doc.extension in STEP_EXTENSIONS:
            text, extracted, preview = analyze_step(path, cfg.storage_dir / "previews", cfg.cad_density_default_g_cm3)
            doc.doc_type = "cad"
            doc.preview_path = str(preview) if preview else None
        elif doc.extension in MESH_EXTENSIONS:
            text, extracted, preview = analyze_stl(path, cfg.storage_dir / "previews", cfg.cad_density_default_g_cm3)
            doc.doc_type = "cad"
            doc.preview_path = str(preview) if preview else None
        elif doc.extension in DXF_EXTENSIONS:
            text, extracted, preview = analyze_dxf(path, cfg.storage_dir / "previews", cfg.cad_density_default_g_cm3)
            doc.doc_type = "cad"
            doc.preview_path = str(preview) if preview else None
        else:
            text, extracted = parse_document(path)
            preview = None

        inferred = infer_metadata(doc.filename, text, doc.extension)
        if doc.extension in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
            drawing = analyze_drawing(path, text, max_pages=cfg.drawing_max_pages)
            if inferred.get("doc_type") == "drawing" or (drawing.get("vector_pdf") or {}).get("engineering_signal_score", 0) >= 0.35 or drawing.get("entities"):
                extracted = {**extracted, "engineering_drawing": drawing}
                facts = drawing.get("normalized_facts") or {}
                if facts.get("material") and not inferred.get("material"):
                    inferred["material"] = facts["material"]
                if facts.get("thickness_mm") is not None and inferred.get("thickness_mm") is None:
                    inferred["thickness_mm"] = facts["thickness_mm"]
                if facts.get("part_number") and not inferred.get("part_number"):
                    inferred["part_number"] = facts["part_number"]
                if facts.get("revision") and not inferred.get("revision"):
                    inferred["revision"] = facts["revision"]
                if inferred.get("doc_type") == "document" and drawing.get("entities"):
                    inferred["doc_type"] = "drawing"
        if not doc.part_number: doc.part_number = inferred.get("part_number")
        if not doc.revision: doc.revision = inferred.get("revision")
        if not doc.doc_type: doc.doc_type = inferred.get("doc_type")
        merged = {**(doc.extracted_metadata or {}), **extracted, **{k:v for k,v in inferred.items() if k not in {"part_number","revision","doc_type"}}}
        doc.extracted_metadata = merged
        # v6.3.2: persist the projection source in PostgreSQL, then atomically commit
        # authoritative engineering state + outbox events. Optional projections never sit
        # inside the document-ingest transaction.
        chunks = chunk_text(text)
        doc.indexed_chunks = persist_document_chunks(db, doc.id, chunks)
        doc.status = DocumentStatus.ready
        register_document(db, doc, commit=False)
        if doc.doc_type == "bom":
            bom_count = ingest_bom_csv(db, doc, path, commit=False)
            if bom_count:
                doc.extracted_metadata = {**doc.extracted_metadata, "bom_items": bom_count}
        db.flush()
        enqueue_document_projections(db, doc, correlation_id=correlation_id)
        db.commit(); db.refresh(doc)
        return doc
    except Exception as exc:
        doc.status = DocumentStatus.failed
        doc.error = f"{type(exc).__name__}: {exc}"
        db.commit()
        return doc
