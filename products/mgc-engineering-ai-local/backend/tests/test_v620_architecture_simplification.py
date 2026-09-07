from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION, BOUNDED_CONTEXTS, PROFILE_FEATURES, RuntimeConfigurationError, available_object_types, runtime_contract
from app.db import models  # noqa: F401
from app.db.migrations import ensure_v620_schema
from app.db.models import BOMItem, ChangeRequest, Document, Part, Project
from app.db.session import Base
from app.integrations.base import ExternalAsset
from app.platform.actions import normalize_action, normalize_decision
from app.platform.connectors import asset_to_envelope
from app.platform.evidence import EvidenceRef, evidence_bundle
from app.services.object360 import object360
from app.core.capability_gate import capability_for_path


def test_v620_schema_marker_is_idempotent():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    ensure_v620_schema(eng); ensure_v620_schema(eng)
    with eng.begin() as c:
        assert c.execute(text("SELECT schema_version FROM mgc_schema_state WHERE id=1")).scalar_one() == "6.2.0"


def test_runtime_contract_has_six_bounded_contexts_and_monotonic_profiles():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"
    assert len(BOUNDED_CONTEXTS) == 6
    assert PROFILE_FEATURES["core"] < PROFILE_FEATURES["ai"] < PROFILE_FEATURES["advanced"]
    out = runtime_contract(Settings(deployment_profile="core", readiness_require_qdrant=True))
    assert out["profile"] == "core"
    assert out["dependencies"]["postgres"]["required"] is True
    assert out["dependencies"]["qdrant"]["required"] is False
    assert out["governance"]["postgres_is_core_store"] is True


def test_ai_profile_requires_qdrant_but_local_ai_is_not_core_readiness_gate():
    cfg = Settings(deployment_profile="ai", readiness_require_qdrant=True)
    assert cfg.semantic_search_enabled is True
    assert cfg.runtime_qdrant_required is True
    out = runtime_contract(cfg)
    assert out["dependencies"]["qdrant"]["required"] is True
    assert out["dependencies"]["local_ai"]["required"] is False


def test_feature_flags_can_disable_advanced_domain_without_disabling_core_invariants():
    cfg = Settings(deployment_profile="advanced", features_disabled="advanced_field,neo4j_projection,postgres_core")
    assert "advanced_field" not in cfg.runtime_features
    assert "neo4j_projection" not in cfg.runtime_features
    assert "postgres_core" in cfg.runtime_features
    assert cfg.runtime_graph_enabled is False


def test_evidence_bundle_is_fail_closed_on_hidden_document():
    values = [
        EvidenceRef("document", "D1", document_id="D1"),
        EvidenceRef("document", "D2", document_id="D2"),
    ]
    assert len(evidence_bundle(values, require_document_visibility={"D1", "D2"})) == 2
    assert evidence_bundle(values, require_document_visibility={"D1"}) == []


def test_action_and_decision_share_one_normalized_contract():
    raw = {"source_id": "A1", "domain": "quality", "title": "Review defect", "priority": "HIGH", "decision_required": True}
    action = normalize_action(raw)
    decision = normalize_decision(raw)
    assert action["priority"] == "high" and action["id"] == "A1"
    assert decision["human_decision_required"] is True
    assert decision["id"] == action["id"]


def test_connector_asset_normalizes_to_canonical_engineering_envelope():
    asset = ExternalAsset(external_id="42", name="Part 42", kind="part", revision="C", part_number="P-42", project_code="CAR", modified_at="2026-09-05T00:00:00Z", metadata={"plant": "A"})
    env = asset_to_envelope("plm", asset).public()
    assert env["source"] == "plm" and env["entity_type"] == "part"
    assert env["external_id"] == "42" and env["payload"]["plant"] == "A"


def test_object360_part_uses_visible_evidence_and_does_not_promote_hidden_change_or_bom():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng); db = Session()
    db.add(Project(code="P1", name="Car", acl_groups=["engineering-ai-users"]))
    db.add(Part(part_number="P-100", name="Bracket", project_code="P1", latest_revision="B"))
    visible = Document(id="D-V", filename="visible.pdf", stored_path="/tmp/v", sha256="1"*64, part_number="P-100", revision="B", doc_type="drawing", project_code="P1", acl_groups=["engineering-ai-users"])
    hidden = Document(id="D-H", filename="hidden.pdf", stored_path="/tmp/h", sha256="2"*64, part_number="P-100", revision="C", doc_type="drawing", project_code="P1", acl_groups=["secret"])
    db.add_all([visible, hidden]); db.flush()
    db.add(BOMItem(parent_part_number="P-100", parent_revision="B", child_part_number="C-V", quantity=1, source_document_id="D-V"))
    db.add(BOMItem(parent_part_number="P-100", parent_revision="C", child_part_number="C-H", quantity=1, source_document_id="D-H"))
    db.add(ChangeRequest(code="ECR-H", title="Hidden change", part_number="P-100", status="review", affected_document_ids=["D-V","D-H"]))
    db.add(ChangeRequest(code="ECR-V", title="Visible change", part_number="P-100", status="review", affected_document_ids=["D-V"]))
    db.commit()
    out = object360(db, "part", "P-100", {"D-V"}, ["engineering-ai-users"])
    assert out is not None and out["identity"]["id"] == "P-100"
    assert [x["part_number"] for x in out["sections"]["bom"]] == ["C-V"]
    assert [x["code"] for x in out["sections"]["changes"]] == ["ECR-V"]
    assert {x["evidence_id"] for x in out["evidence"]} == {"D-V"}
    assert out["governance"]["acl_fail_closed"] is True


def test_invalid_profile_and_cross_profile_feature_enable_fail_closed():
    import pytest
    with pytest.raises(RuntimeConfigurationError):
        runtime_contract(Settings(deployment_profile="advanecd"))
    with pytest.raises(RuntimeConfigurationError):
        _ = Settings(deployment_profile="core", features_enabled="supplier_field").runtime_features


def test_profile_aware_object360_catalog_and_supplier_gate():
    core = Settings(deployment_profile="core").runtime_features
    advanced = Settings(deployment_profile="advanced").runtime_features
    assert available_object_types(core) == ["change", "defect", "part", "requirement", "vin"]
    assert "supplier" in available_object_types(advanced)
    assert capability_for_path("/api/v1/objects/supplier/S-1").feature == "supplier_field"
    assert capability_for_path("/api/v1/projects/P1/supplier-localization").feature == "supplier_field"
    assert capability_for_path("/api/v1/cad/convert").feature == "native_cad_gateway"


def test_object360_supplier_and_vin_field_data_follow_runtime_profile():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng); db = Session()
    db.add(Project(code="P2", name="Car 2", acl_groups=["engineering-ai-users"]))
    d = Document(id="D2", filename="evidence.pdf", stored_path="/tmp/e", sha256="3"*64, project_code="P2", acl_groups=["engineering-ai-users"])
    db.add(d); db.commit()
    core = Settings(deployment_profile="core").runtime_features
    assert object360(db, "supplier", "SUP", {"D2"}, ["engineering-ai-users"], core) is None
