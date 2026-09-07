import hashlib
import mimetypes
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document
from app.services.ingest import ingest_document


def _sha(path: Path) -> tuple[str, int]:
    h = hashlib.sha256(); size = 0
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk); size += len(chunk)
    return h.hexdigest(), size


def scan_inbox(db: Session, acl_groups: list[str] | None = None, project_code: str | None = None) -> dict:
    cfg = get_settings()
    if not cfg.scanner_enabled:
        return {"scanned": 0, "ingested": 0, "skipped": 0, "disabled": True}
    scanned = ingested = skipped = failed = 0
    for source in cfg.inbox_dir.rglob("*"):
        if not source.is_file() or source.suffix.lower() not in cfg.scanner_extension_set:
            continue
        scanned += 1
        digest, size = _sha(source)
        if db.scalar(select(Document.id).where(Document.sha256 == digest).limit(1)):
            skipped += 1; continue
        target_dir = cfg.storage_dir / "uploads"; target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{digest[:16]}_{source.name}"
        shutil.copy2(source, target)
        doc = Document(filename=source.name, stored_path=str(target), source_path=str(source),
                       mime_type=mimetypes.guess_type(source.name)[0] or "application/octet-stream",
                       extension=source.suffix.lower(), size_bytes=size, sha256=digest,
                       acl_groups=acl_groups or ["all"], project_code=project_code)
        db.add(doc); db.commit(); db.refresh(doc)
        ingest_document(db, doc)
        if doc.status.value == "ready": ingested += 1
        else: failed += 1
    return {"scanned": scanned, "ingested": ingested, "skipped": skipped, "failed": failed}
