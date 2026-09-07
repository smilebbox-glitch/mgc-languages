from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core import release_acceptance as ra
from app.core import release_provenance as rp
from app.core import release_provenance_governance as gov
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def make_keypair(tmp_path: Path, name: str = "k") -> tuple[Path, Path]:
    private = tmp_path / f"{name}.key.pem"
    public = tmp_path / f"{name}.pub.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)], check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True, capture_output=True)
    return private, public


def acceptance(release: str = "6.3.34") -> dict:
    return ra.attach_integrity({
        "schema": ra.RELEASE_ACCEPTANCE_SCHEMA,
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "profile": "30",
        "decision": "GO",
        "technical_decision": "GO",
        "production_authorized": False,
        "metrics": {
            "p95_ms": 100.0,
            "p99_ms": 125.0,
            "error_rate": 0.001,
            "requests_per_second": 80.0,
            "db_pool_max_saturation_ratio": 0.5,
            "rto_seconds": 200.0,
            "rpo_seconds": 100.0,
        },
        "chain": {"schema": ra.ACCEPTANCE_CHAIN_SCHEMA, "sequence": 1, "parent_acceptance_sha256": None},
        "baseline_regression": {"baseline_release": "6.3.24"},
        "failed_checks": [],
    })


def sign(doc: dict, private: Path, sig: Path) -> None:
    payload = sig.with_suffix(".payload")
    payload.write_bytes(rp.acceptance_canonical_bytes(doc))
    subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(private), "-out", str(sig), str(payload)], check=True, capture_output=True)
    payload.unlink()


def setup_registry(tmp_path: Path, *, valid_days: int = 180, warning_days: int = 30):
    registry = tmp_path / "registry"
    private, public = make_keypair(tmp_path)
    rp.initialize_registry(registry, registry_id="plant-release-ledger", actor="test")
    rp.register_public_key(registry, key_id="release-key", public_key=public, actor="test", valid_days=valid_days, rotation_warning_days=warning_days)
    return registry, private, public


def register_acceptance(registry: Path, private: Path, tmp_path: Path, release: str = "6.3.34"):
    doc = acceptance(release)
    path = tmp_path / f"acceptance-{release}.json"
    sig = tmp_path / f"acceptance-{release}.sig"
    path.write_text(json.dumps(doc), encoding="utf-8")
    sign(doc, private, sig)
    return rp.register_signed_artifact(registry, kind="acceptance", document_path=path, signature_path=sig, key_id="release-key", actor="test")


def make_adapter(tmp_path: Path, kind: str, *, mismatch: bool = False) -> str:
    script = tmp_path / f"{kind}-adapter.py"
    if kind == "anchor":
        body = f'''import json,sys\nr=json.load(sys.stdin)\nh=r["tip_sha256"]\nprint(json.dumps({{"status":"ANCHORED","provider":"test-anchor","anchor_id":"A-1","tip_sequence":r["tip_sequence"],"tip_sha256":("0"*64 if {mismatch!r} else h),"anchored_at":"2026-09-06T00:00:00Z","receipt":{{"opaque":"ok"}}}}))\n'''
    else:
        body = '''import json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"status":"LOCKED","provider":"test-worm","receipt_id":"W-1","object_sha256":r["object_sha256"],"retain_until":r["retain_until"],"lock_mode":r["lock_mode"],"confirmed_at":"2026-09-06T00:00:00Z","receipt":{"opaque":"locked"}}))\n'''
    script.write_text(body, encoding="utf-8")
    return json.dumps(["python", str(script)])


def test_release_marker():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_new_signing_key_has_bounded_validity(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path, valid_days=90, warning_days=14)
    state = rp.replay_trust_state(rp.load_events(registry))["release-key"]
    assert state["expires_at"] and state["not_before"]
    assert state["rotation_warning_days"] == 14


def test_expired_key_cannot_register_new_acceptance(tmp_path: Path):
    registry = tmp_path / "registry"; rp.initialize_registry(registry, registry_id="r")
    private, public = make_keypair(tmp_path)
    nbf = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat().replace("+00:00", "Z")
    exp = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    rp.register_public_key(registry, key_id="expired", public_key=public, not_before=nbf, expires_at=exp)
    doc = acceptance(); path = tmp_path / "a.json"; sig = tmp_path / "a.sig"
    path.write_text(json.dumps(doc), encoding="utf-8"); sign(doc, private, sig)
    with pytest.raises(rp.ProvenanceError, match="expired"):
        rp.register_signed_artifact(registry, kind="acceptance", document_path=path, signature_path=sig, key_id="expired")


def test_rotation_due_status_is_explicit(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path, valid_days=5, warning_days=30)
    status = gov.key_lifecycle_status(registry)
    assert status["rotation_due_key_ids"] == ["release-key"]
    assert status["expired_key_ids"] == []


def test_retention_policy_is_minimum_retention_without_auto_delete(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path)
    gov.set_retention_policy(registry, policy_id="R-10Y", retention_days={"load": 1460})
    status = gov.retention_status(registry)
    assert status["policy_configured"] is True
    assert status["policy"]["retention_days"]["load"] == 1460
    assert status["automatic_deletion"] is False
    assert status["ledger_metadata_permanent"] is True


def test_legal_hold_lifecycle_is_append_only(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path)
    gov.set_retention_policy(registry, policy_id="R")
    gov.place_legal_hold(registry, hold_id="H-1", reason="audit", release="6.3.34")
    assert gov.retention_status(registry)["active_hold_ids"] == ["H-1"]
    gov.release_legal_hold(registry, hold_id="H-1", reason="audit closed")
    assert gov.retention_status(registry)["active_legal_holds"] == 0


def test_checkpoint_binds_verified_registry_tip(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    register_acceptance(registry, private, tmp_path)
    before = rp.verify_registry(registry)
    event = gov.create_checkpoint(registry)
    assert event["payload"]["covered_tip_sequence"] == before["tip_sequence"]
    assert event["payload"]["covered_tip_sha256"] == before["tip_sha256"]
    assert rp.read_object(registry, event["payload"]["checkpoint_object_sha256"])


def test_external_anchor_receipt_must_match_tip(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path)
    gov.set_retention_policy(registry, policy_id="R")
    command = make_adapter(tmp_path, "anchor", mismatch=True)
    with pytest.raises(rp.ProvenanceError, match="hash mismatch"):
        gov.record_external_anchor(registry, command_json=command)


def test_external_anchor_and_worm_checkpoint_make_governance_pass(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path, valid_days=365, warning_days=30)
    register_acceptance(registry, private, tmp_path)
    gov.set_retention_policy(registry, policy_id="R-10Y")
    gov.create_checkpoint(registry)
    gov.record_external_anchor(registry, command_json=make_adapter(tmp_path, "anchor"))
    gov.seal_latest_checkpoint_to_worm(registry, command_json=make_adapter(tmp_path, "worm"), retain_days=3650)
    result = gov.verify_governance(registry, require_external_anchor=True, require_worm_receipt=True, anchor_max_age_hours=48, checkpoint_max_age_hours=48)
    assert result["status"] == "PASS"
    assert result["external_anchor"]["fresh"] is True
    assert result["worm"]["lock_mode"] == "COMPLIANCE"
    assert result["production_authorized"] is False


def test_missing_external_trust_is_conditional_not_fake_pass(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path, valid_days=365)
    gov.set_retention_policy(registry, policy_id="R")
    result = gov.verify_governance(registry)
    assert result["status"] == "CONDITIONAL"
    assert "external_anchor_missing" in result["warnings"]
    assert "worm_receipt_missing" in result["warnings"]


def test_required_external_trust_fails_closed_when_absent(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path, valid_days=365)
    result = gov.verify_governance(registry, require_external_anchor=True, require_worm_receipt=True)
    assert result["status"] == "FAIL"
    assert "required_external_anchor_unavailable" in result["failures"]
    assert "required_worm_receipt_unavailable" in result["failures"]


def test_offline_auditor_bundle_replays_registry_without_private_keys(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path, valid_days=365)
    register_acceptance(registry, private, tmp_path)
    gov.set_retention_policy(registry, policy_id="R")
    gov.create_checkpoint(registry)
    bundle = tmp_path / "audit.zip"
    exported = gov.export_auditor_bundle(registry, output=bundle)
    assert exported["status"] == "PASS"
    verified = gov.verify_auditor_bundle(bundle)
    assert verified["status"] == "PASS"
    with subprocess.Popen(["unzip", "-l", str(bundle)], stdout=subprocess.PIPE, text=True) as proc:
        listing = proc.communicate()[0]
    assert "PRIVATE KEY" not in listing


def test_tampered_auditor_bundle_fails_offline_verification(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path, valid_days=365)
    register_acceptance(registry, private, tmp_path)
    bundle = tmp_path / "audit.zip"; gov.export_auditor_bundle(registry, output=bundle)
    import zipfile
    corrupt = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(bundle) as src, zipfile.ZipFile(corrupt, "w") as dst:
        changed = False
        for info in src.infolist():
            data = src.read(info)
            if not changed and info.filename.startswith("registry/events/"):
                data += b"x"; changed = True
            dst.writestr(info, data)
    assert gov.verify_auditor_bundle(corrupt)["status"] == "FAIL"


def test_cli_and_operations_expose_governance_without_registry_path():
    root = Path(__file__).resolve().parents[2]
    cli = (root / "scripts/release_provenance_registry.py").read_text(encoding="utf-8")
    ops = (root / "backend/app/api/operations_routes.py").read_text(encoding="utf-8")
    assert all(x in cli for x in ["retention-set", "hold-place", "checkpoint", "anchor", "worm-seal", "auditor-export", "auditor-verify"])
    segment = ops[ops.index('@router.get("/release-provenance")'):ops.index('@router.get("/authoritative-ha")')]
    assert "verify_governance" in segment
    assert '"path"' not in segment


def test_adapter_execution_never_uses_shell_true():
    root = Path(__file__).resolve().parents[2]
    core = (root / "backend/app/core/release_provenance_governance.py").read_text(encoding="utf-8")
    assert "shell=False" in core
    assert "JSON array of argv strings" in core
