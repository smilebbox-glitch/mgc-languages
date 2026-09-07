from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v632_schema
from app.db.models import Document, DocumentSearchChunk, ProjectionDeliveryReceipt, ProjectionOutboxEvent
from app.db.session import Base
from app.services import projection_outbox as po


def _factory(tmp_path: Path | None = None):
    url = "sqlite:///:memory:" if tmp_path is None else f"sqlite:///{tmp_path / 'v632.db'}"
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    return eng, sessionmaker(bind=eng, expire_on_commit=False)


def _doc(path: Path, *, doc_id="D1"):
    return Document(
        id=doc_id,
        filename=path.name,
        stored_path=str(path),
        extension=path.suffix,
        size_bytes=path.stat().st_size,
        sha256="a" * 64,
        project_code="P1",
        manufacturing_area="assembly",
        acl_groups=["engineering"],
        extracted_metadata={"source": "test"},
    )


def test_v632_schema_marker_and_reliability_tables():
    eng, _ = _factory()
    ensure_v632_schema(eng); ensure_v632_schema(eng)
    with eng.begin() as conn:
        assert conn.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.3.2"
        names = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert {"document_search_chunks", "projection_outbox_events", "projection_delivery_receipts"} <= names
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_authoritative_chunks_and_outbox_share_one_rollback_boundary(tmp_path):
    path = tmp_path / "a.txt"; path.write_text("bolt torque 25 Nm")
    _, Factory = _factory()
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.flush()
        po.persist_document_chunks(db, doc.id, ["bolt torque 25 Nm"])
        po.enqueue_event(
            db, target=po.TARGET_SEARCH, event_type="document_index_refresh",
            aggregate_type="document", aggregate_id=doc.id, source_version=po.document_projection_version(db, doc),
            payload={"document_id": doc.id},
        )
        assert db.scalar(select(DocumentSearchChunk)) is not None
        assert db.scalar(select(ProjectionOutboxEvent)) is not None
        db.rollback()
        assert db.scalar(select(DocumentSearchChunk)) is None
        assert db.scalar(select(ProjectionOutboxEvent)) is None


def test_enqueue_is_idempotent_for_same_logical_projection(tmp_path):
    path = tmp_path / "a.txt"; path.write_text("text")
    _, Factory = _factory()
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.flush(); po.persist_document_chunks(db, doc.id, ["text"])
        version = po.document_projection_version(db, doc)
        a = po.enqueue_event(db, target="search", event_type="document_index_refresh", aggregate_type="document", aggregate_id=doc.id, source_version=version)
        b = po.enqueue_event(db, target="search", event_type="document_index_refresh", aggregate_type="document", aggregate_id=doc.id, source_version=version)
        db.commit()
        assert a.id == b.id
        assert len(db.scalars(select(ProjectionOutboxEvent)).all()) == 1


class _FakeSearch:
    mode = "fake_search"
    def __init__(self): self.deleted = []; self.indexed = []
    def delete_document(self, document_id): self.deleted.append(document_id)
    def index_chunks(self, document, chunks): self.indexed.append((document, chunks)); return len(chunks)
    def search(self, *args, **kwargs): return []


class _FailSearch(_FakeSearch):
    def index_chunks(self, document, chunks): raise RuntimeError("projection unavailable")


def test_search_delivery_is_effectively_once_and_receipted(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"; path.write_text("station instruction")
    _, Factory = _factory()
    fake = _FakeSearch(); monkeypatch.setattr(po, "get_search_port", lambda: fake)
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.flush(); po.persist_document_chunks(db, doc.id, ["station instruction"])
        event = po.enqueue_event(db, target="search", event_type="document_index_refresh", aggregate_type="document", aggregate_id=doc.id, source_version=po.document_projection_version(db, doc))
        event.status = "processing"; event.attempt_count = 1; db.commit(); eid = event.id
    with Factory() as db:
        out = po.process_projection_event(db, eid)
        assert out["status"] == "succeeded"
        assert db.scalar(select(ProjectionDeliveryReceipt).where(ProjectionDeliveryReceipt.event_id == eid)) is not None
    # A duplicate logical invocation is short-circuited by the local receipt.
    with Factory() as db:
        event = db.get(ProjectionOutboxEvent, eid); event.status = "processing"; db.commit()
        out = po.process_projection_event(db, eid)
        assert out["status"] == "succeeded"
    assert len(fake.indexed) == 1


def test_failure_moves_to_dlq_at_retry_budget(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"; path.write_text("text")
    _, Factory = _factory()
    monkeypatch.setattr(po, "get_search_port", lambda: _FailSearch())
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.flush(); po.persist_document_chunks(db, doc.id, ["text"])
        event = po.enqueue_event(db, target="search", event_type="document_index_refresh", aggregate_type="document", aggregate_id=doc.id, source_version=po.document_projection_version(db, doc))
        event.status = "processing"; event.attempt_count = 1; event.max_attempts = 1; db.commit(); eid = event.id
        out = po.process_projection_event(db, eid)
        assert out["status"] == "dead_letter"
        assert "projection unavailable" in out["error"]
        replayed = po.replay_dead_letter(db, eid)
        assert replayed is not None and replayed.status == "retry"
        assert replayed.max_attempts > replayed.attempt_count


def test_older_projection_event_is_superseded_by_new_authoritative_chunks(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"; path.write_text("v1")
    _, Factory = _factory()
    fake = _FakeSearch(); monkeypatch.setattr(po, "get_search_port", lambda: fake)
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.flush(); po.persist_document_chunks(db, doc.id, ["v1"])
        event = po.enqueue_event(db, target="search", event_type="document_index_refresh", aggregate_type="document", aggregate_id=doc.id, source_version=po.document_projection_version(db, doc))
        event.status = "processing"; event.attempt_count = 1
        po.persist_document_chunks(db, doc.id, ["v2 changed"])
        db.commit(); eid = event.id
        out = po.process_projection_event(db, eid)
        assert out["status"] == "superseded"
    assert fake.indexed == []


def test_rebuild_backfills_legacy_text_document_before_event_generation(tmp_path, monkeypatch):
    path = tmp_path / "legacy.txt"; path.write_text("legacy operator instruction bolt 25 Nm", encoding="utf-8")
    _, Factory = _factory()
    class _Cfg:
        semantic_search_enabled = True
        runtime_object_store_enabled = False
        runtime_graph_enabled = False
        projection_max_attempts = 8
    monkeypatch.setattr(po, "get_settings", lambda: _Cfg())
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.commit()
        out = po.enqueue_rebuild(db, target="search")
        assert out["legacy_documents_backfilled"] == 1
        assert out["events_created"] == 1
        chunks = db.scalars(select(DocumentSearchChunk).where(DocumentSearchChunk.document_id == doc.id)).all()
        assert chunks and "legacy operator instruction" in chunks[0].text


def test_projection_health_never_claims_optional_projection_failure_blocks_core(tmp_path):
    path = tmp_path / "a.txt"; path.write_text("x")
    _, Factory = _factory()
    with Factory() as db:
        doc = _doc(path); db.add(doc); db.flush(); po.persist_document_chunks(db, doc.id, ["x"])
        event = po.enqueue_event(db, target="search", event_type="document_index_refresh", aggregate_type="document", aggregate_id=doc.id, source_version=po.document_projection_version(db, doc))
        event.status = "dead_letter"; event.completed_at = po.utcnow(); db.commit()
        health = po.projection_health(db)
        assert health["status"] == "degraded"
        assert health["dead_letter"] == 1
        assert health["policy"]["optional_projection_failure_blocks_core"] is False
