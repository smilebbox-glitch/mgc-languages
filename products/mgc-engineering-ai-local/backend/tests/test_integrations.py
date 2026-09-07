from pathlib import Path

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentStatus, ExternalObject, ExternalObjectVersion, ExternalSystem, IntegrationRun
from app.db.session import Base
from app.integrations.base import ExternalAsset
from app.integrations.cad_gateway import CadGatewayConnector
from app.integrations.mounted_folder import MountedFolderConnector
from app.integrations.registry import build_connector, supported_connector_types


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_registry_exposes_enterprise_connector_types():
    types = supported_connector_types()
    assert {"mounted_folder", "plm_rest", "pdm_rest", "erp_rest", "bom_rest", "cad_gateway"}.issubset(types)


def test_secret_references_resolve_from_environment(monkeypatch):
    monkeypatch.setenv("TEST_PLM_TOKEN", "secret-token")
    c = build_connector("plm_rest", {"base_url": "http://example"}, {"token_env": "TEST_PLM_TOKEN"})
    assert c.auth_headers()["Authorization"] == "Bearer secret-token"


def test_raw_secret_is_not_accepted_by_registry():
    c = build_connector("plm_rest", {"base_url": "http://example"}, {"token": "must-not-be-used"})
    assert "Authorization" not in c.auth_headers()


def test_mounted_folder_connector_pages_and_fetches(tmp_path: Path):
    share = tmp_path / "share"; share.mkdir()
    (share / "a.txt").write_text("A", encoding="utf-8")
    (share / "b.pdf").write_bytes(b"PDF")
    (share / "ignore.exe").write_bytes(b"X")
    c = MountedFolderConnector({"path": str(share), "extensions": [".txt", ".pdf"]})
    assert c.health().ok is True
    first = c.list_assets(limit=1)
    assert len(first.assets) == 1 and first.next_cursor == "1"
    second = c.list_assets(first.next_cursor, limit=10)
    assert len(second.assets) == 1 and second.next_cursor is None
    out = c.fetch_asset(first.assets[0], tmp_path / "out")
    assert out.exists()


def test_cad_gateway_conversion_records_sdk_headers(tmp_path: Path):
    source = tmp_path / "part.CATPart"; source.write_bytes(b"native")
    step_bytes = b"ISO-10303-21;\nEND-ISO-10303-21;\n"

    def handler(request: httpx.Request):
        if request.url.path == "/convert":
            return httpx.Response(200, content=step_bytes, headers={"X-CAD-SDK": "TEST-SDK", "X-CAD-SDK-Version": "9.1"})
        return httpx.Response(200, json={"status": "ok"})

    c = CadGatewayConnector({"base_url": "http://cad"})
    c.client = httpx.Client(transport=httpx.MockTransport(handler))
    target, meta = c.convert(source, "step")
    assert target.read_bytes() == step_bytes
    assert meta["sdk"] == "TEST-SDK"
    assert meta["sdk_version"] == "9.1"
    assert meta["source_format"] == ".catpart"


def test_sync_is_idempotent_and_preserves_immutable_history(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module
    from app.integrations.base import ConnectorHealth, SyncPage

    state = {"fingerprint": "v1", "content": b"hello"}

    class FakeConnector:
        connector_type = "fake"
        def health(self): return ConnectorHealth(True, "ok")
        def list_assets(self, cursor=None, limit=100):
            if cursor: return SyncPage([])
            return SyncPage([ExternalAsset(
                external_id="X-1", name="8450012345_REV_D_note.txt", kind="document",
                part_number="8450012345", revision="D", modified_at=state["fingerprint"], content=state["content"]
            )])
        def fetch_asset(self, asset, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            p = target_dir / asset.name; p.write_bytes(asset.content or b"")
            return p

    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: FakeConnector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")

    def fake_ingest(db, doc):
        doc.status = DocumentStatus.ready
        doc.doc_type = "document"
        db.commit(); db.refresh(doc)
        return doc
    monkeypatch.setattr(sync_module, "_ingest", fake_ingest)

    db = _db_session()
    system = ExternalSystem(code="test", name="Test", connector_type="plm_rest", config_json={}, secret_config_json={}, acl_groups=["all"])
    db.add(system); db.commit(); db.refresh(system)
    first = sync_module.sync_external_system(db, system, ["all"])
    second = sync_module.sync_external_system(db, system, ["all"])
    assert first["imported"] == 1
    assert second["imported"] == 0 and second["skipped"] == 1

    first_doc = db.scalars(select(Document).order_by(Document.created_at)).first()
    first_path = Path(first_doc.stored_path)
    assert first_path.read_bytes() == b"hello"

    state["fingerprint"] = "v2"
    state["content"] = b"world"
    third = sync_module.sync_external_system(db, system, ["all"])
    assert third["imported"] == 1
    docs = db.scalars(select(Document).order_by(Document.created_at)).all()
    assert len(docs) == 2
    assert first_path.read_bytes() == b"hello"
    assert Path(docs[1].stored_path).read_bytes() == b"world"
    assert docs[0].stored_path != docs[1].stored_path

    obj = db.scalar(select(ExternalObject).where(ExternalObject.system_id == system.id, ExternalObject.external_id == "X-1"))
    assert obj is not None and obj.document_id == docs[1].id
    versions = db.scalars(select(ExternalObjectVersion).where(ExternalObjectVersion.system_id == system.id, ExternalObjectVersion.external_id == "X-1")).all()
    assert len(versions) == 2
    assert {v.sha256 for v in versions} == {d.sha256 for d in docs}
    assert len(db.scalars(select(IntegrationRun).where(IntegrationRun.system_id == system.id)).all()) == 3


def test_webhook_signature_accepts_valid_and_rejects_replay():
    import hashlib, hmac
    from app.integrations.webhook import verify_signature
    body = b'{"event":"changed"}'
    timestamp = "1000"
    secret = "test-secret"
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert verify_signature(body, timestamp, "sha256=" + digest, secret, max_skew_seconds=300, now=1000)
    assert not verify_signature(body, timestamp, "sha256=" + digest, secret, max_skew_seconds=300, now=1401)
    assert not verify_signature(body + b"x", timestamp, "sha256=" + digest, secret, max_skew_seconds=300, now=1000)


def test_generic_rest_supports_incremental_checkpoint():
    from app.integrations.generic_rest import GenericEngineeringRestConnector
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"items": [], "next_cursor": None, "checkpoint": "cp-42"})
    c = GenericEngineeringRestConnector({"base_url": "http://plm"})
    c.client = httpx.Client(transport=httpx.MockTransport(handler))
    page = c.list_assets()
    assert page.checkpoint == "cp-42"
    assert page.next_cursor is None


def test_sync_persists_checkpoint_separately_from_pagination(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module
    from app.integrations.base import SyncPage
    from app.db.models import SyncCursor

    class CheckpointConnector:
        connector_type = "fake"
        def list_assets(self, cursor=None, limit=100):
            assert cursor is None
            return SyncPage([], next_cursor=None, checkpoint="checkpoint-v2")

    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: CheckpointConnector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")
    db = _db_session()
    system = ExternalSystem(code="cp", name="Checkpoint", connector_type="plm_rest", config_json={}, secret_config_json={}, acl_groups=["all"])
    db.add(system); db.commit(); db.refresh(system)
    result = sync_module.sync_external_system(db, system, ["all"])
    assert result["status"] == "ok"
    cursor = db.scalar(select(SyncCursor).where(SyncCursor.system_id == system.id))
    assert cursor.cursor == "checkpoint-v2"


def test_identical_bytes_from_different_systems_do_not_share_document_acl(tmp_path: Path, monkeypatch):
    from app.integrations import sync as sync_module
    from app.integrations.base import SyncPage

    class SameBytesConnector:
        def list_assets(self, cursor=None, limit=100):
            return SyncPage([ExternalAsset(external_id="OBJ", name="same.txt", kind="document", modified_at="v1", content=b"same")])
        def fetch_asset(self, asset, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True); p=target_dir/asset.name; p.write_bytes(asset.content); return p

    monkeypatch.setattr(sync_module, "build_connector", lambda *a, **k: SameBytesConnector())
    monkeypatch.setattr(sync_module.get_settings(), "storage_dir", tmp_path / "storage")
    def fake_ingest(db, doc):
        doc.status = DocumentStatus.ready; db.commit(); db.refresh(doc); return doc
    monkeypatch.setattr(sync_module, "_ingest", fake_ingest)

    db = _db_session()
    a = ExternalSystem(code="a", name="A", connector_type="plm_rest", config_json={}, secret_config_json={}, acl_groups=["team-a"])
    b = ExternalSystem(code="b", name="B", connector_type="plm_rest", config_json={}, secret_config_json={}, acl_groups=["team-b"])
    db.add_all([a,b]); db.commit(); db.refresh(a); db.refresh(b)
    sync_module.sync_external_system(db, a, ["team-a"])
    sync_module.sync_external_system(db, b, ["team-b"])
    docs = db.scalars(select(Document).order_by(Document.created_at)).all()
    assert len(docs) == 2
    assert docs[0].sha256 == docs[1].sha256
    assert docs[0].id != docs[1].id
    assert {tuple(d.acl_groups) for d in docs} == {("team-a",), ("team-b",)}


def test_http_connector_oauth_client_credentials_and_cache(monkeypatch):
    from app.integrations.generic_rest import GenericEngineeringRestConnector
    calls = {"token": 0, "assets": 0}
    def handler(request: httpx.Request):
        if request.url.path == "/token":
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": "oauth-token", "expires_in": 3600})
        calls["assets"] += 1
        assert request.headers.get("authorization") == "Bearer oauth-token"
        return httpx.Response(200, json={"items": [], "next_cursor": None})
    c = GenericEngineeringRestConnector({
        "base_url": "http://plm",
        "oauth_token_url": "http://auth/token",
        "oauth_client_id": "mgc",
    }, {"oauth_client_secret": "secret"})
    c.client = httpx.Client(transport=httpx.MockTransport(handler))
    c.list_assets(); c.list_assets()
    assert calls["token"] == 1
    assert calls["assets"] == 2


def test_cad_gateway_auto_target_uses_authoritative_response_header(tmp_path: Path):
    source = tmp_path / "drawing.grb"; source.write_bytes(b"native")
    pdf_bytes = b"%PDF-1.4\n%%EOF\n"
    def handler(request: httpx.Request):
        if request.url.path == "/convert":
            return httpx.Response(200, content=pdf_bytes, headers={
                "Content-Type": "application/pdf",
                "X-CAD-Target-Format": "pdf",
                "X-CAD-Vendor": "tflex",
                "X-CAD-SDK": "T-FLEX Open API",
                "X-CAD-SDK-Version": "17",
            })
        return httpx.Response(200, json={"status": "ok"})
    c = CadGatewayConnector({"base_url": "http://cad", "vendor": "tflex"})
    c.client = httpx.Client(transport=httpx.MockTransport(handler))
    target, meta = c.convert(source, "auto")
    assert target.suffix == ".pdf"
    assert target.read_bytes() == pdf_bytes
    assert meta["target_format"] == "pdf"
    assert meta["vendor"] == "tflex"
