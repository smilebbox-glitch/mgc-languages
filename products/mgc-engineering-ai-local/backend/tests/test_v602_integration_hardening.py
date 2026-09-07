from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus, ExternalObject, ExternalSystem, IntegrationIngestEvent, IntegrationRun
from app.db.session import Base
from app.integrations.base import ExternalAsset, SyncPage
from app.services.integration_hardening import calculate_data_quality, contract_for, validate_asset_contract


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _fake_ingest(db, doc):
    doc.status = DocumentStatus.ready
    doc.doc_type = doc.doc_type or "document"
    db.commit(); db.refresh(doc)
    return doc


def test_quality_components_are_explainable_and_freshness_degrades():
    system = ExternalSystem(
        code="plm", name="PLM", connector_type="plm_rest", source_domain="plm",
        expected_freshness_minutes=60, required_fields=["external_id", "name", "kind", "modified_at"],
    )
    contract = contract_for(system)
    now = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
    fresh = ExternalAsset(external_id="A", name="a.pdf", kind="drawing", modified_at=(now - timedelta(minutes=10)).isoformat())
    old = ExternalAsset(external_id="B", name="b.pdf", kind="drawing", modified_at=(now - timedelta(hours=8)).isoformat())
    vf = validate_asset_contract(fresh, contract, now=now)
    vo = validate_asset_contract(old, contract, now=now)
    qf = calculate_data_quality(fresh, contract, vf, payload_sha256="a" * 64, now=now)
    qo = calculate_data_quality(old, contract, vo, payload_sha256="b" * 64, now=now)
    assert vf["valid"] is True and vo["valid"] is True
    assert qf["freshness"]["status"] == "FRESH"
    assert qo["freshness"]["status"] == "STALE"
    assert qf["score"] > qo["score"]
    assert set(qf["components"]) == {"schema", "completeness", "freshness", "identity", "provenance"}


def test_legacy_non_iso_modified_fingerprint_is_not_blocking_without_freshness_contract():
    system = ExternalSystem(code="legacy", name="Legacy", connector_type="plm_rest", required_fields=[])
    asset = ExternalAsset(external_id="X", name="x.txt", kind="document", modified_at="v17")
    validation = validate_asset_contract(asset, contract_for(system))
    assert validation["valid"] is True
    assert any(x["code"] == "INVALID_SOURCE_TIMESTAMP" for x in validation["warnings"])


def test_contract_violation_goes_to_quarantine_and_can_be_replayed_after_contract_fix(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module

    asset = ExternalAsset(
        external_id="OBJ-1", name="obj.json", kind="record",
        modified_at="2026-09-04T17:50:00+00:00",
        metadata={"status": "released"},
    )

    class Connector:
        def list_assets(self, cursor=None, limit=100):
            return SyncPage([asset], next_cursor=None, checkpoint="cp-1")
        def fetch_asset(self, asset, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            p = target_dir / asset.name
            p.write_text('{"status":"released"}', encoding="utf-8")
            return p

    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: Connector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")
    monkeypatch.setattr(sync_module, "_ingest", _fake_ingest)

    db = _db()
    system = ExternalSystem(
        code="qms", name="QMS", connector_type="qms_rest", source_domain="qms",
        expected_freshness_minutes=10_000_000,
        required_fields=["external_id", "name", "kind", "metadata.failure_code"],
        acl_groups=["quality"],
    )
    db.add(system); db.commit(); db.refresh(system)
    result = sync_module.sync_external_system(db, system, ["quality"])
    assert result["status"] == "partial"
    assert result["quarantined"] == 1 and result["imported"] == 0
    event = db.scalar(select(IntegrationIngestEvent).where(IntegrationIngestEvent.system_id == system.id))
    assert event is not None and event.status == "quarantined"
    assert event.quarantine_path and Path(event.quarantine_path).is_file()
    assert db.scalar(select(Document)) is None

    # Administrator fixes the declared contract/mapping; immutable quarantined bytes are replayed.
    system.required_fields = ["external_id", "name", "kind"]
    db.commit()
    replay = sync_module.replay_quarantined_event(db, system, event)
    assert replay["replayed"] is True and replay["status"] == "replayed"
    doc = db.get(Document, replay["document_id"])
    assert doc is not None and doc.status == DocumentStatus.ready
    assert doc.acl_groups == ["quality"]
    obj = db.scalar(select(ExternalObject).where(ExternalObject.system_id == system.id, ExternalObject.external_id == "OBJ-1"))
    assert obj is not None and obj.data_confidence_level in {"HIGH", "MEDIUM", "LOW"}
    assert (obj.data_quality_json or {}).get("components", {}).get("schema") == 1.0
    replay_run = db.get(IntegrationRun, replay["run_id"])
    assert replay_run.replayed_count == 1


def test_sync_ledger_is_idempotent_and_does_not_duplicate_accepted_event(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module

    asset = ExternalAsset(external_id="P-1", name="part.txt", kind="document", revision="D", content=b"same")

    class Connector:
        def list_assets(self, cursor=None, limit=100): return SyncPage([asset])
        def fetch_asset(self, asset, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            p = target_dir / asset.name; p.write_bytes(asset.content or b""); return p

    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: Connector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")
    monkeypatch.setattr(sync_module, "_ingest", _fake_ingest)
    db = _db()
    system = ExternalSystem(code="plm", name="PLM", connector_type="plm_rest", source_domain="plm", acl_groups=["all"])
    db.add(system); db.commit(); db.refresh(system)
    a = sync_module.sync_external_system(db, system, ["all"])
    b = sync_module.sync_external_system(db, system, ["all"])
    assert a["imported"] == 1
    assert b["skipped"] == 1 and b["imported"] == 0
    events = db.scalars(select(IntegrationIngestEvent).where(IntegrationIngestEvent.system_id == system.id)).all()
    assert len(events) == 1 and events[0].status == "accepted"
    assert len(db.scalars(select(Document)).all()) == 1


def test_mes_and_qms_connector_types_are_exposed():
    from app.integrations.registry import supported_connector_types
    assert {"mes_rest", "qms_rest"}.issubset(set(supported_connector_types()))


def test_generic_rest_record_mode_persists_inline_json_without_content_endpoint(tmp_path: Path):
    from app.integrations.generic_rest import GenericEngineeringRestConnector
    asset = ExternalAsset(
        external_id="Q-1", name="quality-record", kind="quality_record",
        metadata={"id": "Q-1", "failure_code": "F-22", "count": 3},
    )
    c = GenericEngineeringRestConnector({"base_url": "http://qms", "record_mode": True})
    target = c.fetch_asset(asset, tmp_path)
    assert target.suffix == ".json"
    text = target.read_text(encoding="utf-8")
    assert '"failure_code": "F-22"' in text


def test_weak_source_identity_uses_payload_digest_and_detects_changed_bytes(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module

    state = {"content": b"one"}
    asset = ExternalAsset(external_id="WEAK-1", name="weak.txt", kind="document")

    class Connector:
        def list_assets(self, cursor=None, limit=100): return SyncPage([asset])
        def fetch_asset(self, asset, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            p = target_dir / asset.name; p.write_bytes(state["content"]); return p

    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: Connector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")
    monkeypatch.setattr(sync_module, "_ingest", _fake_ingest)
    db = _db()
    system = ExternalSystem(code="weak", name="Weak", connector_type="engineering_rest", acl_groups=["all"])
    db.add(system); db.commit(); db.refresh(system)
    first = sync_module.sync_external_system(db, system, ["all"])
    second = sync_module.sync_external_system(db, system, ["all"])
    state["content"] = b"two"
    third = sync_module.sync_external_system(db, system, ["all"])
    assert first["imported"] == 1
    assert second["skipped"] == 1
    assert third["imported"] == 1
    assert len(db.scalars(select(Document)).all()) == 2
    assert len(db.scalars(select(IntegrationIngestEvent)).all()) == 2


def test_system_quality_freshness_decays_at_read_time():
    from app.services.integration_hardening import aggregate_system_quality
    now = datetime(2026, 9, 4, 18, 0, tzinfo=timezone.utc)
    row = ExternalObject(
        system_id="S", external_id="A", source_modified_at=now - timedelta(minutes=10),
        data_confidence_score=1.0,
        data_quality_json={
            "score": 1.0, "level": "HIGH", "blocking": False,
            "components": {"schema": 1.0, "completeness": 1.0, "freshness": 1.0, "identity": 1.0, "provenance": 1.0},
            "freshness": {"status": "FRESH"},
        },
    )
    fresh = aggregate_system_quality([row], expected_freshness_minutes=60, now=now)
    stale = aggregate_system_quality([row], expected_freshness_minutes=60, now=now + timedelta(hours=10))
    assert fresh["level"] == "HIGH"
    assert stale["score"] < fresh["score"]
    assert stale["freshness_status_counts"].get("STALE") == 1


def test_source_metadata_cannot_override_mgc_provenance(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module
    asset = ExternalAsset(
        external_id="P-SEC", name="p.txt", kind="document", revision="A", content=b"x",
        metadata={"external_system": "spoofed", "data_quality": {"level": "HIGH"}, "ingest_event_id": "fake"},
    )
    class Connector:
        def list_assets(self, cursor=None, limit=100): return SyncPage([asset])
        def fetch_asset(self, asset, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True); p = target_dir / asset.name; p.write_bytes(asset.content or b""); return p
    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: Connector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")
    monkeypatch.setattr(sync_module, "_ingest", _fake_ingest)
    db = _db()
    system = ExternalSystem(code="plm-sec", name="PLM", connector_type="plm_rest", source_domain="plm", acl_groups=["all"])
    db.add(system); db.commit(); db.refresh(system)
    result = sync_module.sync_external_system(db, system, ["all"])
    assert result["imported"] == 1
    doc = db.scalar(select(Document))
    assert doc.extracted_metadata["external_system"] == "plm-sec"
    assert doc.extracted_metadata["ingest_event_id"] != "fake"
    assert doc.extracted_metadata["data_quality"]["components"]["schema"] == 1.0


def test_postgres_integration_sync_lock_uses_dedicated_connection_and_unlocks(monkeypatch):
    from app.integrations import sync as sync_module

    class Result:
        def __init__(self, value): self.value = value
        def scalar(self): return self.value
    class Conn:
        def __init__(self): self.calls = []; self.committed = False
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, statement, params):
            sql = str(statement)
            self.calls.append(sql)
            return Result(True if "pg_try_advisory_lock" in sql else True)
        def commit(self): self.committed = True
    class Dialect: name = "postgresql"
    class Bind:
        dialect = Dialect()
        def __init__(self, conn): self.conn = conn
        def connect(self): return self.conn
    class DB:
        def __init__(self, bind): self.bind = bind
        def get_bind(self): return self.bind

    conn = Conn(); db = DB(Bind(conn))
    with sync_module.integration_sync_lock(db, "system-1"):
        pass
    assert any("pg_try_advisory_lock" in x for x in conn.calls)
    assert any("pg_advisory_unlock" in x for x in conn.calls)
    assert conn.committed is True


def test_postgres_integration_sync_lock_has_bounded_busy_failure(monkeypatch):
    from app.integrations import sync as sync_module

    class Result:
        def scalar(self): return False
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, statement, params): return Result()
        def commit(self): pass
    class Dialect: name = "postgresql"
    class Bind:
        dialect = Dialect()
        def connect(self): return Conn()
    class DB:
        def get_bind(self): return Bind()

    times = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(sync_module.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(sync_module.time, "sleep", lambda _x: None)
    monkeypatch.setattr(sync_module.get_settings(), "integration_sync_lock_timeout_seconds", 1)
    import pytest
    with pytest.raises(sync_module.IntegrationSyncBusy):
        with sync_module.integration_sync_lock(DB(), "system-2"):
            pass
