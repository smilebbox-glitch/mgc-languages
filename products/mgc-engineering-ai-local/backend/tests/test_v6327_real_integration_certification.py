from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.db.models import ExternalObject, ExternalSystem, IntegrationIngestEvent, IntegrationRun
from app.integrations.base import ConnectorHealth, ExternalAsset, SyncPage
from app.services import integration_certification as cert


def _db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


def _system(domain="plm", **overrides):
    config = {
        "base_url": "https://gateway.internal.example",
        "certification": {
            "declared_capabilities": list(cert.DOMAIN_PROFILES[domain]["required_capabilities"]),
            "checkpoint_mode": "fingerprint",
            "degraded_mode": "cached_read_only",
            "writeback_enabled": False,
            "enforce_for_sync": True,
        },
    }
    fields = dict(
        id=f"sys-{domain}", code=f"{domain}1", name=domain.upper(), connector_type=f"{domain}_rest",
        enabled=True, config_json=config, secret_config_json={"token_env": "MGC_TEST_TOKEN"},
        acl_groups=["all"], source_domain=domain, contract_version="mgc-integration-v1",
        expected_freshness_minutes=60, required_fields=list(cert.DOMAIN_PROFILES[domain]["recommended_required_fields"]),
    )
    fields.update(overrides)
    return ExternalSystem(**fields)


class _FakeConnector:
    def __init__(self, *, deterministic=True, checkpoint=None, empty=False, health=True):
        self.deterministic = deterministic
        self.checkpoint = checkpoint
        self.empty = empty
        self.health_ok = health
        self.calls = 0

    def health(self):
        return ConnectorHealth(self.health_ok, "ok" if self.health_ok else "down", latency_ms=1.2)

    def list_assets(self, cursor=None, limit=20):
        self.calls += 1
        if self.empty:
            items = []
        else:
            rev = "A" if self.deterministic or self.calls == 1 else "B"
            items = [ExternalAsset(
                external_id="OBJ-1", name="obj.json", kind="document", revision=rev,
                part_number="P1", project_code="P", modified_at="2026-09-06T07:00:00Z",
                metadata={"external_id": "OBJ-1", "name": "obj.json", "kind": "document", "revision": rev, "part_number": "P1", "modified_at": "2026-09-06T07:00:00Z"},
            )]
        return SyncPage(items, next_cursor=None, checkpoint=self.checkpoint)


def test_all_enterprise_domains_have_explicit_certification_profiles():
    assert set(cert.DOMAIN_PROFILES) == {"plm", "pdm", "erp", "mes", "qms"}
    for domain, profile in cert.DOMAIN_PROFILES.items():
        assert "idempotent_replay" in profile["required_capabilities"]
        assert "cached_read_only" in profile["required_capabilities"]


def test_static_contract_passes_for_fully_declared_plm_adapter():
    out = cert.static_contract_report(_system("plm"))
    assert out["decision"] == "PASS"
    assert out["production_authorized"] is False


def test_static_contract_is_conditional_when_capability_declaration_missing():
    s = _system("erp")
    s.config_json = {**s.config_json, "certification": {**s.config_json["certification"], "declared_capabilities": []}}
    out = cert.static_contract_report(s)
    assert out["decision"] == "CONDITIONAL"
    assert any(x["code"] == "CAPABILITY_DECLARATION" and x["status"] == "CONDITIONAL" for x in out["checks"])


def test_static_contract_rejects_writeback_and_raw_secret_config():
    s = _system("mes")
    s.config_json = {**s.config_json, "token": "raw-secret", "certification": {**s.config_json["certification"], "writeback_enabled": True}}
    out = cert.static_contract_report(s)
    assert out["decision"] == "NO_GO"
    assert any(x["code"] == "WRITEBACK_DISABLED" and x["status"] == "FAIL" for x in out["checks"])
    assert any(x["code"] == "NO_RAW_SECRETS_IN_CONFIG" and x["status"] == "FAIL" for x in out["checks"])


def test_static_contract_requires_https_except_explicit_local_simulator():
    s = _system("qms")
    s.config_json = {**s.config_json, "base_url": "http://qms.internal"}
    assert cert.static_contract_report(s)["decision"] == "NO_GO"
    s.config_json = {**s.config_json, "base_url": "http://integration-simulator", "certification": {**s.config_json["certification"], "allow_local_http": True}}
    assert cert.static_contract_report(s)["decision"] == "PASS"


def test_live_probe_proves_deterministic_read_and_idempotent_replay(monkeypatch):
    fake = _FakeConnector()
    monkeypatch.setattr(cert, "build_connector", lambda *a, **k: fake)
    out = cert.live_contract_probe(_system("plm"), sample_limit=5)
    assert out["decision"] == "PASS"
    assert out["sample_count"] == 1
    assert any(x["code"] == "DETERMINISTIC_FIRST_PAGE" and x["status"] == "PASS" for x in out["checks"])
    assert any(x["code"] == "IDEMPOTENT_REPLAY_KEYS" and x["status"] == "PASS" for x in out["checks"])
    assert "external_id" not in out["samples"][0]


def test_live_probe_fails_on_non_deterministic_same_cursor_read(monkeypatch):
    monkeypatch.setattr(cert, "build_connector", lambda *a, **k: _FakeConnector(deterministic=False))
    out = cert.live_contract_probe(_system("pdm"))
    assert out["decision"] == "NO_GO"
    assert any(x["code"] == "DETERMINISTIC_FIRST_PAGE" and x["status"] == "FAIL" for x in out["checks"])


def test_live_probe_source_checkpoint_mode_requires_stable_checkpoint(monkeypatch):
    s = _system("erp")
    s.config_json = {**s.config_json, "certification": {**s.config_json["certification"], "checkpoint_mode": "source_checkpoint"}}
    monkeypatch.setattr(cert, "build_connector", lambda *a, **k: _FakeConnector(checkpoint=None))
    out = cert.live_contract_probe(s)
    assert out["decision"] == "NO_GO"
    assert any(x["code"] == "SOURCE_CHECKPOINT" and x["status"] == "FAIL" for x in out["checks"])


def test_live_probe_empty_source_is_conditional_not_fake_pass(monkeypatch):
    monkeypatch.setattr(cert, "build_connector", lambda *a, **k: _FakeConnector(empty=True))
    out = cert.live_contract_probe(_system("qms"))
    assert out["decision"] == "CONDITIONAL"
    assert out["sample_count"] == 0


def test_live_probe_health_failure_is_no_go(monkeypatch):
    monkeypatch.setattr(cert, "build_connector", lambda *a, **k: _FakeConnector(health=False))
    out = cert.live_contract_probe(_system("mes"))
    assert out["decision"] == "NO_GO"
    assert out["sample_count"] == 0


def test_runtime_posture_degrades_to_cached_read_only_on_source_failure():
    db = _db(); s = _system("plm", id=None); db.add(s); db.commit(); db.refresh(s)
    s.last_health_status = "failed"
    db.add(ExternalObject(system_id=s.id, external_id="X", name="x", object_type="document", last_seen_at=datetime.now(timezone.utc)))
    db.commit()
    out = cert.runtime_posture(db, s)
    assert out["mode"] == "DEGRADED_READ_ONLY"
    assert out["cached_engineering_reads_allowed"] is True
    assert out["authoritative_source_mutation_allowed"] is False


def test_runtime_posture_blocks_when_source_failed_and_no_cache():
    db = _db(); s = _system("erp", id=None); db.add(s); db.commit(); db.refresh(s)
    s.last_health_status = "failed"; db.commit()
    out = cert.runtime_posture(db, s)
    assert out["mode"] == "BLOCKED"
    assert out["cached_engineering_reads_allowed"] is False


def test_runtime_posture_degrades_on_quarantine_ratio_and_low_sync_success():
    db = _db(); s = _system("qms", id=None); db.add(s); db.commit(); db.refresh(s)
    for i in range(2):
        db.add(ExternalObject(system_id=s.id, external_id=f"O{i}", name="x", object_type="document", last_seen_at=datetime.now(timezone.utc)))
    db.add(IntegrationIngestEvent(system_id=s.id, idempotency_key="k", external_id="bad", status="quarantined"))
    db.add(IntegrationRun(system_id=s.id, status="failed", failed_count=1))
    db.commit()
    out = cert.runtime_posture(db, s)
    assert out["mode"] == "DEGRADED_READ_ONLY"
    assert "QUARANTINE_RATIO_EXCEEDED" in out["reasons"]


def test_sync_guard_is_fail_closed_only_when_policy_enforcement_enabled():
    db = _db(); s = _system("mes", id=None); db.add(s); db.commit(); db.refresh(s)
    s.last_health_status = "failed"; db.commit()
    allowed, posture = cert.sync_allowed(db, s)
    assert allowed is False and posture["mode"] == "BLOCKED"
    s.config_json = {**s.config_json, "certification": {**s.config_json["certification"], "enforce_for_sync": False}}
    db.commit()
    allowed, _ = cert.sync_allowed(db, s)
    assert allowed is True

def test_mgcctl_exposes_integration_certification_action():
    import importlib.util, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("mgcctl_v6327_int", root / "scripts/mgcctl.py")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    ns = module.build_parser().parse_args(["certify", "integration", "--contract", "ops/integrations/contracts/plm.example.json", "--dry-run", "--json"])
    assert ns.certify_action == "integration"
    assert ns.func(ns) == 0
