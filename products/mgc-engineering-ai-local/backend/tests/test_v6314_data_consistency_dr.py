from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401
from app.db.migrations import ensure_v6313_schema
from app.db.models import Document, Relationship
from app.db.session import Base
from app.services.dr_consistency import build_consistency_snapshot, compare_consistency_snapshots


def _factory(tmp_path: Path):
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v6313_schema(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False), tmp_path.resolve()


def _doc(db, storage: Path, name: str = "evidence.txt", content: bytes = b"controlled evidence") -> Document:
    p = storage / "uploads" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    row = Document(
        filename=name,
        stored_path=str(p),
        mime_type="text/plain",
        extension=".txt",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        status=models.DocumentStatus.ready,
    )
    db.add(row); db.commit(); db.refresh(row)
    return row


def test_v6314_consistency_snapshot_passes_for_matching_db_and_evidence(tmp_path: Path):
    _, Factory, storage = _factory(tmp_path / "storage")
    storage.mkdir(parents=True)
    with Factory() as db:
        doc = _doc(db, storage)
        db.add(Relationship(subject_type="document", subject_id=doc.id, predicate="evidence_for", object_type="part", object_id="P1", evidence_document_id=doc.id))
        db.commit()
        report = build_consistency_snapshot(db, storage_root=storage, hash_files=True, hash_database=True, epoch_id="epoch-1")
        assert report["status"] == "pass"
        assert report["critical_findings"] == 0
        assert report["policy"]["backup_eligible"] is True
        assert len(report["database"]["logical_sha256"]) == 64
        assert len(report["storage"]["tree_sha256"]) == 64
        assert report["documents"]["files_hashed"] == 1
        assert report["document_references"]["dangling"] == 0


def test_v6314_detects_evidence_content_corruption(tmp_path: Path):
    _, Factory, storage = _factory(tmp_path / "storage")
    storage.mkdir(parents=True)
    with Factory() as db:
        doc = _doc(db, storage)
        Path(doc.stored_path).write_bytes(b"tampered evidence")
        report = build_consistency_snapshot(db, storage_root=storage, hash_files=True, hash_database=False)
        assert report["status"] == "fail"
        assert any(x["code"] in {"document_size_mismatch", "document_sha256_mismatch"} for x in report["findings"])


def test_v6314_detects_dangling_digital_thread_document_reference(tmp_path: Path):
    _, Factory, storage = _factory(tmp_path / "storage")
    storage.mkdir(parents=True)
    with Factory() as db:
        doc = _doc(db, storage)
        db.add(Relationship(subject_type="part", subject_id="P1", predicate="verified_by", object_type="document", object_id=doc.id, evidence_document_id="missing-document"))
        db.commit()
        report = build_consistency_snapshot(db, storage_root=storage, hash_files=True, hash_database=False)
        assert report["status"] == "fail"
        assert report["document_references"]["dangling"] >= 1
        assert any(x["code"] == "dangling_document_reference" for x in report["findings"])


def test_v6314_exact_restore_compare_rejects_database_drift(tmp_path: Path):
    _, Factory, storage = _factory(tmp_path / "storage")
    storage.mkdir(parents=True)
    with Factory() as db:
        doc = _doc(db, storage)
        expected = build_consistency_snapshot(db, storage_root=storage, hash_files=True, hash_database=True, epoch_id="backup-epoch")
        doc.filename = "changed-after-backup.txt"
        db.commit()
        actual = build_consistency_snapshot(db, storage_root=storage, hash_files=True, hash_database=True)
        comparison = compare_consistency_snapshots(expected, actual)
        assert comparison["status"] == "fail"
        assert comparison["checks"]["database_logical_sha256"] is False
        assert comparison["checks"]["storage_tree_sha256"] is True


def test_v6314_storage_symlink_is_fail_closed(tmp_path: Path):
    _, Factory, storage = _factory(tmp_path / "storage")
    storage.mkdir(parents=True)
    outside = tmp_path / "outside.txt"; outside.write_text("outside", encoding="utf-8")
    link = storage / "linked.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with Factory() as db:
        report = build_consistency_snapshot(db, storage_root=storage, hash_files=True, hash_database=False)
        assert report["status"] == "fail"
        assert report["storage"]["symlinks"] == 1
        assert any(x["code"] == "storage_symlink" for x in report["findings"])
