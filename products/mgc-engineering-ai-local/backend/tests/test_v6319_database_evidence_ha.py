from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core import authoritative_ha as ah
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def settings(tmp_path: Path, **kw):
    base = dict(
        database_ha_enabled=True,
        database_ha_expected_system_identifier="123456",
        database_ha_require_primary_for_writes=True,
        evidence_ha_enabled=True,
        evidence_ha_mode="shared",
        evidence_ha_require_active_for_writes=True,
        evidence_ha_cluster_id="evidence-prod-01",
        evidence_ha_marker_relative_path=".mgc-ha/STORAGE_EPOCH.json",
        authoritative_write_fence_enabled=True,
        storage_dir=tmp_path,
    )
    base.update(kw)
    return SimpleNamespace(**base)


class Result:
    def __init__(self, value): self.value = value
    def scalar_one(self): return self.value
    def scalar_one_or_none(self): return self.value


class FakeConn:
    def __init__(self, *, recovery=False, read_only="off", system_identifier="123456", schema_version="6.3.13"):
        self.recovery=recovery; self.read_only=read_only; self.system_identifier=system_identifier; self.schema_version=schema_version; self.closed=False
    def execute(self, stmt):
        sql=str(stmt)
        if "pg_is_in_recovery" in sql: return Result(self.recovery)
        if "transaction_read_only" in sql: return Result(self.read_only)
        if "pg_control_system" in sql: return Result(self.system_identifier)
        if "mgc_schema_state" in sql: return Result(self.schema_version)
        raise AssertionError(sql)
    def close(self): self.closed=True


class FakeEngine:
    dialect=SimpleNamespace(name="postgresql")
    def __init__(self, conn): self.conn=conn
    def connect(self): return self.conn


def write_marker(root: Path, *, state="active", generation=1, cluster_id="evidence-prod-01", db_id="123456"):
    path=root/".mgc-ha"/"STORAGE_EPOCH.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": ah.MARKER_SCHEMA,
        "cluster_id": cluster_id,
        "database_system_identifier": db_id,
        "generation": generation,
        "state": state,
        "production_authorized": False,
    }), encoding="utf-8")
    return path


def test_release_marker_without_schema_change():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_writable_primary_with_expected_cluster_is_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    db=ah.database_authority_probe(bind=FakeEngine(FakeConn()))
    assert db.safe and db.role == "primary" and db.writable
    assert db.expected_system_identifier_match is True


def test_standby_is_never_write_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    db=ah.database_authority_probe(bind=FakeEngine(FakeConn(recovery=True, read_only="on")))
    assert not db.safe and db.role == "standby" and not db.writable


def test_wrong_postgres_system_identifier_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    db=ah.database_authority_probe(bind=FakeEngine(FakeConn(system_identifier="other")))
    assert not db.safe and db.expected_system_identifier_match is False
    assert db.detail == "unexpected_database_cluster"




def test_wrong_schema_marker_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    db=ah.database_authority_probe(bind=FakeEngine(FakeConn(schema_version="6.3.12")))
    assert not db.safe and db.expected_schema_match is False
    assert db.detail == "database_schema_marker_mismatch"


def test_missing_schema_marker_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    db=ah.database_authority_probe(bind=FakeEngine(FakeConn(schema_version=None)))
    assert not db.safe and db.expected_schema_match is False
    assert db.detail == "database_schema_marker_unavailable"


def test_symlinked_evidence_marker_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    real=tmp_path/"real-marker.json"
    real.write_text(json.dumps({
        "schema": ah.MARKER_SCHEMA, "cluster_id": "evidence-prod-01",
        "database_system_identifier": "123456", "generation": 1, "state": "active"
    }), encoding="utf-8")
    marker=tmp_path/".mgc-ha"/"STORAGE_EPOCH.json"
    marker.parent.mkdir(parents=True)
    marker.symlink_to(real)
    with pytest.raises(ah.AuthoritativeWriteFence):
        ah.read_evidence_marker()


def test_active_evidence_generation_bound_to_database_is_safe(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    write_marker(tmp_path)
    db=ah.DatabaseAuthority(True, True, "primary", True, False, False, "123456", True, "6.3.13", True, True, "ok")
    ev=ah.evidence_authority_probe(database=db)
    assert ev.safe and ev.state == "active" and ev.generation == 1


def test_standby_or_wrong_database_binding_fences_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    write_marker(tmp_path, state="standby")
    db=ah.DatabaseAuthority(True, True, "primary", True, False, False, "123456", True, "6.3.13", True, True, "ok")
    assert not ah.evidence_authority_probe(database=db).safe
    write_marker(tmp_path, state="active", db_id="999")
    ev=ah.evidence_authority_probe(database=db)
    assert not ev.safe and ev.database_system_identifier_match is False


def test_missing_marker_fails_closed_when_evidence_ha_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    db=ah.DatabaseAuthority(True, True, "primary", True, False, False, "123456", True, "6.3.13", True, True, "ok")
    ev=ah.evidence_authority_probe(database=db)
    assert not ev.safe and ev.marker_present is False


def test_write_fence_raises_on_unproven_authority(monkeypatch, tmp_path):
    monkeypatch.setattr(ah, "get_settings", lambda: settings(tmp_path))
    monkeypatch.setattr(ah, "authoritative_ha_snapshot", lambda connection=None: {"enabled":True,"status":"UNSAFE","write_safe":False})
    with pytest.raises(ah.AuthoritativeWriteFence):
        ah.assert_authoritative_write_safe()


def test_mutating_method_gate_only_targets_writes():
    assert all(ah.should_fence_http_method(x) for x in ("POST","PUT","PATCH","DELETE"))
    assert not ah.should_fence_http_method("GET")
    assert not ah.should_fence_http_method("HEAD")


def test_evidence_marker_cli_requires_recovery_point_and_increments_generation(tmp_path):
    storage=tmp_path/"storage"; storage.mkdir()
    script=Path("scripts/evidence_ha_marker.py")
    subprocess.run([sys.executable,str(script),"--storage",str(storage),"init","--cluster-id","evidence-prod-01","--database-system-identifier","123456","--state","standby"],check=True,capture_output=True,text=True)
    rp=tmp_path/"rp.json"
    rp.write_text(json.dumps({
        "schema":"mgc-authoritative-recovery-point-v1","database_system_identifier":"123456",
        "evidence_cluster_id":"evidence-prod-01","evidence_generation":1,
        "database_logical_sha256":"a"*64,"evidence_tree_sha256":"b"*64,"consistency_epoch_id":"epoch-1"
    }),encoding="utf-8")
    subprocess.run([sys.executable,str(script),"--storage",str(storage),"promote","--cluster-id","evidence-prod-01","--database-system-identifier","123456","--expected-generation","1","--recovery-point",str(rp),"--confirm","PROMOTE_EVIDENCE"],check=True,capture_output=True,text=True)
    marker=json.loads((storage/".mgc-ha"/"STORAGE_EPOCH.json").read_text())
    assert marker["state"] == "active" and marker["generation"] == 2
    assert marker["production_authorized"] is False


def test_authoritative_operational_marker_is_excluded_from_evidence_fingerprint_and_backup():
    dr=Path("backend/app/services/dr_consistency.py").read_text()
    backup=Path("scripts/backup_core.sh").read_text()
    assert '".mgc-ha"' in dr
    assert "--exclude='./.mgc-ha'" in backup


def test_http_and_session_write_fences_cover_api_and_workers():
    main=Path("backend/app/main.py").read_text()
    session=Path("backend/app/db/session.py").read_text()
    assert "AuthoritativeWriteGateMiddleware" in main
    assert '"before_flush"' in session and '"do_orm_execute"' in session and '"before_commit"' in session
    assert "assert_authoritative_write_safe" in session


def test_authoritative_ha_compose_requires_external_writer_and_storage():
    src=Path("docker-compose.authoritative-ha.yml").read_text()
    assert "DATABASE_URL:?" in src
    assert "DATABASE_HA_EXPECTED_SYSTEM_IDENTIFIER:?" in src
    assert "MGC_STORAGE_PATH:?" in src
    assert "EVIDENCE_HA_CLUSTER_ID:?" in src
    assert "application_does_not_promote" not in src  # policy belongs to runtime, not deceptive compose automation
