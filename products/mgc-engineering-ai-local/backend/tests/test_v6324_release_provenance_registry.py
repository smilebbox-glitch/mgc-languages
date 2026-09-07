from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.core import release_acceptance as ra
from app.core import release_provenance as rp
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION


def make_keypair(tmp_path: Path, name: str = "k") -> tuple[Path, Path]:
    private = tmp_path / f"{name}.key.pem"
    public = tmp_path / f"{name}.pub.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private)], check=True, capture_output=True)
    subprocess.run(["openssl", "pkey", "-in", str(private), "-pubout", "-out", str(public)], check=True, capture_output=True)
    return private, public


def sign_document(document: dict, private: Path, out: Path) -> Path:
    payload = rp.acceptance_canonical_bytes(document)
    payload_path = out.with_suffix(".payload")
    payload_path.write_bytes(payload)
    subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(private), "-out", str(out), str(payload_path)], check=True, capture_output=True)
    payload_path.unlink()
    return out


def acceptance(release: str, *, profile: str = "30", p95: float = 100.0, rps: float = 80.0) -> dict:
    doc = {
        "schema": ra.RELEASE_ACCEPTANCE_SCHEMA,
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "decision": "GO",
        "technical_decision": "GO",
        "production_authorized": False,
        "metrics": {
            "p95_ms": p95,
            "p99_ms": p95 * 1.25,
            "error_rate": 0.001,
            "requests_per_second": rps,
            "db_pool_max_saturation_ratio": 0.5,
            "rto_seconds": 200.0,
            "rpo_seconds": 100.0,
        },
        "chain": {"schema": ra.ACCEPTANCE_CHAIN_SCHEMA, "sequence": 1, "parent_acceptance_sha256": None},
        "baseline_regression": {"baseline_release": None},
        "failed_checks": [],
    }
    return ra.attach_integrity(doc)


def baseline(release: str, source_sha: str, *, profile: str = "30") -> dict:
    doc = {
        "schema": ra.APPROVED_BASELINE_SCHEMA,
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "technical_decision": "GO",
        "human_approved": True,
        "bootstrap": False,
        "approval": {"reference": "CHG-6324", "approved_at": "2026-09-06T00:00:00Z"},
        "metrics": acceptance(release, profile=profile)["metrics"],
        "source_acceptance_sha256": source_sha,
        "source_chain_sequence": 1,
        "source_parent_acceptance_sha256": None,
    }
    return ra.attach_integrity(doc)


def setup_registry(tmp_path: Path):
    registry = tmp_path / "registry"
    private, public = make_keypair(tmp_path)
    rp.initialize_registry(registry, registry_id="plant-release-ledger", actor="test")
    rp.register_public_key(registry, key_id="release-2026-q3", public_key=public, actor="test")
    return registry, private, public


def register_acceptance(registry: Path, private: Path, tmp_path: Path, release: str, *, p95: float = 100.0, rps: float = 80.0):
    doc = acceptance(release, p95=p95, rps=rps)
    path = tmp_path / f"acceptance-{release}.json"
    sig = tmp_path / f"acceptance-{release}.json.sig"
    path.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
    sign_document(doc, private, sig)
    return rp.register_signed_artifact(registry, kind="acceptance", document_path=path, signature_path=sig, key_id="release-2026-q3", actor="test")


def test_release_marker():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_registry_initializes_append_only_chain(tmp_path: Path):
    registry = tmp_path / "registry"
    event = rp.initialize_registry(registry, registry_id="r1")
    assert event["sequence"] == 1 and event["parent_event_sha256"] is None
    verified = rp.verify_registry(registry)
    assert verified["status"] == "PASS" and verified["tip_sequence"] == 1
    with pytest.raises(rp.ProvenanceError):
        rp.initialize_registry(registry, registry_id="r2")


def test_public_key_registration_never_accepts_private_key(tmp_path: Path):
    registry = tmp_path / "registry"; rp.initialize_registry(registry, registry_id="r")
    private, public = make_keypair(tmp_path)
    with pytest.raises(rp.ProvenanceError):
        rp.register_public_key(registry, key_id="bad", public_key=private)
    event = rp.register_public_key(registry, key_id="good", public_key=public)
    assert event["payload"]["key_id"] == "good"
    with pytest.raises(rp.ProvenanceError):
        rp.register_public_key(registry, key_id="good", public_key=public)


def test_signed_acceptance_is_verified_and_content_addressed(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    event = register_acceptance(registry, private, tmp_path, "6.3.23")
    assert event["event_type"] == "ACCEPTANCE_REGISTERED"
    assert event["payload"]["signature_verified"] is True
    result = rp.verify_registry(registry)
    assert result["status"] == "PASS" and result["verified_signed_artifacts"] == 1
    for ref in event["objects"]:
        assert rp.object_path(registry, ref["sha256"]).is_file()


def test_revocation_blocks_new_artifacts_but_preserves_historical_verification(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    register_acceptance(registry, private, tmp_path, "6.3.23")
    rp.revoke_public_key(registry, key_id="release-2026-q3", reason="rotation")
    assert rp.verify_registry(registry)["status"] == "PASS"
    doc = acceptance("6.3.24"); path = tmp_path / "new.json"; sig = tmp_path / "new.sig"
    path.write_text(json.dumps(doc), encoding="utf-8"); sign_document(doc, private, sig)
    with pytest.raises(rp.ProvenanceError, match="revoked"):
        rp.register_signed_artifact(registry, kind="acceptance", document_path=path, signature_path=sig, key_id="release-2026-q3")


def test_rotation_uses_new_key_id_and_both_history_segments_verify(tmp_path: Path):
    registry, private1, _public1 = setup_registry(tmp_path)
    register_acceptance(registry, private1, tmp_path, "6.3.23")
    rp.revoke_public_key(registry, key_id="release-2026-q3", reason="scheduled rotation")
    private2, public2 = make_keypair(tmp_path, "k2")
    rp.register_public_key(registry, key_id="release-2026-q4", public_key=public2)
    doc = acceptance("6.3.24"); path = tmp_path / "a24.json"; sig = tmp_path / "a24.sig"
    path.write_text(json.dumps(doc), encoding="utf-8"); sign_document(doc, private2, sig)
    rp.register_signed_artifact(registry, kind="acceptance", document_path=path, signature_path=sig, key_id="release-2026-q4")
    result = rp.verify_registry(registry)
    assert result["status"] == "PASS" and result["verified_signed_artifacts"] == 2
    summary = rp.registry_summary(registry)
    assert summary["active_key_ids"] == ["release-2026-q4"] and summary["revoked_key_ids"] == ["release-2026-q3"]


def test_tampered_content_addressed_object_fails_verification(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    event = register_acceptance(registry, private, tmp_path, "6.3.23")
    obj = rp.object_path(registry, event["payload"]["document_object_sha256"])
    os.chmod(obj, 0o640); obj.write_bytes(obj.read_bytes() + b"\n")
    result = rp.verify_registry(registry)
    assert result["status"] == "FAIL"


def test_event_filename_or_chain_tamper_is_detected(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    register_acceptance(registry, private, tmp_path, "6.3.23")
    event_file = sorted((registry / "events").glob("*.json"))[-1]
    wrong = event_file.with_name("99999999-" + event_file.name.split("-", 1)[1])
    event_file.rename(wrong)
    result = rp.verify_event_chain(registry)
    assert result["status"] == "FAIL" and any("filename" in f["reasons"] or "sequence" in f["reasons"] for f in result["failures"])


def test_symlinked_registry_component_is_refused(tmp_path: Path):
    real = tmp_path / "real"; real.mkdir()
    link = tmp_path / "registry"; link.symlink_to(real, target_is_directory=True)
    with pytest.raises(rp.ProvenanceError, match="symlink"):
        rp.initialize_registry(link, registry_id="r")


def test_approved_baseline_is_registered_with_human_approval_metadata(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    acc_event = register_acceptance(registry, private, tmp_path, "6.3.23")
    b = baseline("6.3.23", acc_event["payload"]["canonical_sha256"])
    path = tmp_path / "baseline.json"; sig = tmp_path / "baseline.sig"
    path.write_text(json.dumps(b), encoding="utf-8"); sign_document(b, private, sig)
    event = rp.register_signed_artifact(registry, kind="baseline", document_path=path, signature_path=sig, key_id="release-2026-q3")
    assert event["payload"]["human_approved"] is True
    assert event["payload"]["approval_reference"] == "CHG-6324"
    assert rp.verify_registry(registry)["status"] == "PASS"


def test_unsigned_failover_object_may_be_archived_but_is_not_claimed_signed(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path)
    doc = {"schema": "mgc-target-host-evidence-v1", "release": "6.3.24", "profile": "30", "failover": {"rto_seconds": 120, "rpo_seconds": 60}}
    path = tmp_path / "failover.json"; path.write_text(json.dumps(doc), encoding="utf-8")
    event = rp.register_signed_artifact(registry, kind="failover", document_path=path, signature_path=None, key_id=None)
    assert event["payload"]["signature_verified"] is False
    assert rp.verify_registry(registry)["status"] == "PASS"


def test_cross_version_regression_comparison_uses_registered_metrics(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    register_acceptance(registry, private, tmp_path, "6.3.23", p95=100, rps=100)
    register_acceptance(registry, private, tmp_path, "6.3.24", p95=110, rps=95)
    comp = rp.compare_releases(registry, release_a="6.3.23", release_b="6.3.24", profile="30")
    assert comp["metrics"]["p95_ms"]["ratio_b_over_a"] == pytest.approx(1.1)
    assert comp["metrics"]["requests_per_second"]["ratio_b_over_a"] == pytest.approx(.95)


def test_audit_report_summarizes_release_chain_without_authorizing_production(tmp_path: Path):
    registry, private, _public = setup_registry(tmp_path)
    register_acceptance(registry, private, tmp_path, "6.3.23")
    report = rp.build_audit_report(registry)
    assert report["registry_verification"]["status"] == "PASS"
    assert report["releases"][0]["release"] == "6.3.23"
    assert report["production_authorized"] is False


def test_concurrent_appends_are_serialized(tmp_path: Path):
    registry, _private, _public = setup_registry(tmp_path)
    def add(i: int):
        return rp.append_event(registry, event_type="FAILOVER_EVIDENCE_REGISTERED", actor=f"t{i}", payload={"release": "6.3.24", "profile": "30", "i": i}, objects=[])
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(add, range(8)))
    result = rp.verify_event_chain(registry, verify_objects=True)
    assert result["status"] == "PASS" and result["tip_sequence"] == 10


def test_source_contracts_expose_registry_without_private_keys():
    root = Path(__file__).resolve().parents[2]
    script = (root / "scripts/release_provenance_registry.py").read_text(encoding="utf-8")
    core = (root / "backend/app/core/release_provenance.py").read_text(encoding="utf-8")
    assert "key-revoke" in script and "acceptance-register" in script and "audit" in script
    assert "PRIVATE KEY" in core and "must never enter" in core
    assert "fcntl.LOCK_EX" in core

def test_uninitialized_registry_is_not_reported_healthy(tmp_path: Path):
    registry = tmp_path / "registry"
    assert rp.verify_registry(registry)["status"] == "FAIL"
    assert rp.registry_summary(registry)["status"] == "UNINITIALIZED"
    _private, public = make_keypair(tmp_path)
    with pytest.raises(rp.ProvenanceError, match="not initialized"):
        rp.register_public_key(registry, key_id="x", public_key=public)


def test_release_pipeline_and_baseline_promotion_can_append_to_registry():
    root = Path(__file__).resolve().parents[2]
    pipeline = (root / "scripts/release_acceptance_pipeline.py").read_text(encoding="utf-8")
    promotion = (root / "scripts/promote_acceptance_baseline.py").read_text(encoding="utf-8")
    wrapper = (root / "scripts/automated_release_acceptance.sh").read_text(encoding="utf-8")
    assert "--provenance-registry" in pipeline and "kind=\"acceptance\"" in pipeline
    assert "--provenance-registry" in promotion and "kind='baseline'" in promotion
    assert "RELEASE_PROVENANCE_REGISTRY" in wrapper and "RELEASE_PROVENANCE_KEY_ID" in wrapper
