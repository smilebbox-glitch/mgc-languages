from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.db.models import (
    ExternalObject, ExternalSystem, IntegrationEntityMapping, IntegrationRun,
    ManufacturingBOMItem, Part, Project, ReleaseBaseline, VehicleBuild,
)
from app.services.integration_reconciliation import (
    authority_conflicts, build_reconciliation_report, canonical_target_exists,
    mapping_coverage, reconcile_ebom_mbom_sources, reconcile_mes_genealogy,
    reconcile_qms_links, source_facts,
)


def _db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)


def _quality():
    return {
        "score": 1.0, "level": "HIGH", "blocking": False,
        "components": {"schema": 1.0, "completeness": 1.0, "freshness": 1.0, "identity": 1.0, "provenance": 1.0},
        "freshness": {"status": "FRESH"},
    }


def _system(db, code, domain, role=None, authoritative_for=None, project="P603"):
    rec = {"project_code": project}
    if role: rec["role"] = role
    if authoritative_for is not None: rec["authoritative_for"] = authoritative_for
    row = ExternalSystem(
        code=code, name=code.upper(), connector_type=f"{domain}_rest", source_domain=domain,
        expected_freshness_minutes=60, acl_groups=["all"], config_json={"reconciliation": rec},
    )
    db.add(row); db.commit(); db.refresh(row)
    return row


def _obj(db, system, external_id, kind, meta, revision=None, part_number=None, fp=None, when=None):
    when = when or datetime.now(timezone.utc)
    row = ExternalObject(
        system_id=system.id, external_id=external_id, object_type=kind,
        name=f"{external_id}.json", part_number=part_number, revision=revision,
        metadata_json={"project_code": "P603", **meta}, source_fingerprint=fp or f"fp-{external_id}",
        source_modified_at=when, data_confidence_score=1.0, data_confidence_level="HIGH",
        data_quality_json=_quality(), last_seen_at=when,
    )
    db.add(row); db.commit(); db.refresh(row)
    return row


def _seed_canonical(db):
    p = Project(code="P603", name="Pilot", root_part_number="ROOT", acl_groups=["all"])
    db.add(p)
    db.add_all([
        Part(part_number="ROOT", name="Root", project_code="P603", latest_revision="A"),
        Part(part_number="P1", name="Part 1", project_code="P603", latest_revision="D"),
    ])
    db.commit()
    db.add(ManufacturingBOMItem(
        project_code="P603", parent_part_number="ROOT", parent_revision="A",
        child_part_number="P1", child_revision="D", quantity=1, unit="pcs", position="10",
        supplier_code="SUP1", source_system="erp",
    ))
    db.commit()
    base = ReleaseBaseline(
        project_code="P603", code="REL603", name="Release", baseline_type="release",
        root_part_number="ROOT", status="frozen", fingerprint="f" * 64,
        snapshot_json={"schema": "mgc-release-baseline-v3", "manufacturing_bom": [
            {"parent_part_number": "ROOT", "child_part_number": "P1", "child_revision": "D", "quantity": 1, "unit": "pcs", "position": "10"}
        ]}, source_document_ids=[], created_by="test",
    )
    db.add(base); db.commit(); db.refresh(base)
    build = VehicleBuild(
        project_code="P603", code="B1", vehicle_identifier="VIN001", plant="PLANT1",
        build_type="series_observation", status="completed", release_baseline_id=base.id,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(build); db.commit(); db.refresh(build)
    return p, base, build


def _seed_sources(db, *, mbom_revision="D", mes_revision="D", qms_part="P1"):
    now = datetime.now(timezone.utc)
    plm = _system(db, "plm1", "plm", "ebom")
    erp = _system(db, "erp1", "erp", "mbom")
    mes = _system(db, "mes1", "mes", "genealogy")
    qms = _system(db, "qms1", "qms", "defects")
    common = {"parent_part_number": "ROOT", "child_part_number": "P1", "quantity": 1, "unit": "pcs", "position": "10", "supplier_code": "SUP1"}
    _obj(db, plm, "EB-1", "ebom_item", {**common, "child_revision": "D"}, when=now)
    _obj(db, erp, "MB-1", "mbom_item", {**common, "child_revision": mbom_revision}, when=now)
    _obj(db, mes, "GEN-1", "genealogy_item", {"vin": "VIN001", "part_number": "P1", "revision": mes_revision, "supplier_code": "SUP1"}, when=now)
    _obj(db, qms, "DEF-1", "defect_record", {"defect_code": "F01", "vin": "VIN001", "part_number": qms_part, "supplier_code": "SUP1", "count": 1}, when=now)
    for system in (plm, erp, mes, qms):
        db.add(IntegrationRun(system_id=system.id, status="ok", imported_count=1, started_at=now, finished_at=now))
    db.commit()
    return plm, erp, mes, qms


def test_cross_system_ebom_mbom_reconciliation_detects_revision_mismatch():
    db = _db(); _seed_canonical(db); _seed_sources(db, mbom_revision="C")
    facts = source_facts(db, "P603")
    out = reconcile_ebom_mbom_sources(facts)
    assert out["status"] == "MISMATCH"
    assert out["summary"]["changed"] == 1
    assert out["changed"][0]["changes"]["child_revision"] == {"from": "D", "to": "C"}
    assert out["no_automatic_source_write"] is True


def test_mapping_registry_resolves_alias_and_turns_stale_when_source_changes():
    db = _db(); _seed_canonical(db)
    plm = _system(db, "plm-alias", "plm", "ebom")
    obj = _obj(db, plm, "EB-A", "ebom_item", {"parent_part_number": "ROOT", "child_part_number": "P-ALIAS", "child_revision": "D", "quantity": 1}, fp="one")
    mapping = IntegrationEntityMapping(
        system_id=plm.id, project_code="P603", source_entity_type="part", source_external_id=obj.external_id,
        source_key="P-ALIAS", canonical_entity_type="part", canonical_key="P1", status="confirmed",
        mapping_method="manual", source_fingerprint="one", last_verified_at=datetime.now(timezone.utc), created_by="admin",
    )
    db.add(mapping); db.commit()
    facts = source_facts(db, "P603")
    first = mapping_coverage(db, "P603", facts)
    assert first["unmatched"] == 0 and first["coverage"] == 1.0
    obj.source_fingerprint = "two"; db.commit()
    second = mapping_coverage(db, "P603", facts)
    assert second["stale"] == 1
    assert any("SOURCE_FINGERPRINT_CHANGED" in x["reasons"] for x in second["stale_mappings"])


def test_mapping_identity_supports_multiple_part_keys_in_one_bom_record():
    db = _db(); _seed_canonical(db)
    plm = _system(db, "plm-multi", "plm", "ebom")
    obj = _obj(db, plm, "ROW-1", "ebom_item", {"parent_part_number": "ROOT_ALIAS", "child_part_number": "P1_ALIAS", "quantity": 1})
    db.add_all([
        IntegrationEntityMapping(system_id=plm.id, project_code="P603", source_entity_type="part", source_external_id=obj.external_id, source_key="ROOT_ALIAS", canonical_entity_type="part", canonical_key="ROOT", status="confirmed", source_fingerprint=obj.source_fingerprint),
        IntegrationEntityMapping(system_id=plm.id, project_code="P603", source_entity_type="part", source_external_id=obj.external_id, source_key="P1_ALIAS", canonical_entity_type="part", canonical_key="P1", status="confirmed", source_fingerprint=obj.source_fingerprint),
    ])
    db.commit()
    assert len(db.scalars(select(IntegrationEntityMapping)).all()) == 2
    cov = mapping_coverage(db, "P603", source_facts(db, "P603"))
    assert cov["coverage"] == 1.0


def test_mes_genealogy_is_checked_against_release_baseline_not_guesswork():
    db = _db(); _seed_canonical(db); _seed_sources(db, mes_revision="D")
    facts = source_facts(db, "P603")
    ok = reconcile_mes_genealogy(db, "P603", facts)
    assert ok["status"] == "MATCH" and ok["matched"] == 1
    mes = db.scalar(select(ExternalSystem).where(ExternalSystem.code == "mes1"))
    obj = db.scalar(select(ExternalObject).where(ExternalObject.system_id == mes.id))
    obj.metadata_json = {**obj.metadata_json, "revision": "C"}; obj.revision = "C"; db.commit()
    bad = reconcile_mes_genealogy(db, "P603", source_facts(db, "P603"))
    assert bad["status"] == "MISMATCH" and bad["mismatches"] == 1
    assert bad["no_mes_write"] is True


def test_qms_defect_linkage_reports_unmatched_part_without_inventing_link():
    db = _db(); _seed_canonical(db); _seed_sources(db, qms_part="UNKNOWN-PART")
    out = reconcile_qms_links(db, "P603", source_facts(db, "P603"))
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["fully_linked"] == 0 and out["partial"] == 1
    assert out["partial_items"][0]["links"]["part"] is False
    assert out["no_qms_write"] is True


def test_multiple_explicit_authorities_are_not_silently_resolved():
    db = _db(); _seed_canonical(db)
    a = _system(db, "plm-a", "plm", "ebom", authoritative_for=["ebom"])
    b = _system(db, "plm-b", "plm", "ebom", authoritative_for=["ebom"])
    _obj(db, a, "A", "ebom_item", {"parent_part_number": "ROOT", "child_part_number": "P1", "child_revision": "C"})
    _obj(db, b, "B", "ebom_item", {"parent_part_number": "ROOT", "child_part_number": "P1", "child_revision": "D"})
    out = authority_conflicts(db, "P603", source_facts(db, "P603"))
    assert out["status"] == "CONFLICT"
    assert out["explicit_authority_conflicts"][0]["reason"] == "MULTIPLE_EXPLICIT_AUTHORITIES"
    assert out["no_automatic_winner_selection"] is True


def test_pilot_acceptance_is_ready_only_when_roles_mapping_freshness_and_sync_are_good():
    db = _db(); _seed_canonical(db); _seed_sources(db)
    report = build_reconciliation_report(db, "P603")
    assert report["schema"] == "mgc-reconciliation-v1"
    assert report["mapping_coverage"]["coverage"] == 1.0
    assert report["ebom_vs_mbom"]["status"] == "MATCH"
    assert report["mes_vs_released_configuration"]["status"] == "MATCH"
    assert report["qms_entity_linkage"]["fully_linked"] == 1
    assert report["pilot_acceptance"]["status"] == "READY_FOR_CONTROLLED_PILOT"
    assert report["pilot_acceptance"]["human_go_live_approval_required"] is True


def test_pilot_acceptance_fails_closed_when_required_sources_are_missing():
    db = _db(); _seed_canonical(db)
    plm = _system(db, "plm-only", "plm", "ebom")
    _obj(db, plm, "E", "ebom_item", {"parent_part_number": "ROOT", "child_part_number": "P1", "child_revision": "D"})
    out = build_reconciliation_report(db, "P603")
    assert out["pilot_acceptance"]["status"] == "NOT_READY"
    assert any(x["code"] == "REQUIRED_SOURCE_ROLES" for x in out["pilot_acceptance"]["blockers"])


def test_time_decaying_freshness_blocks_pilot_after_source_sla_expires():
    db = _db(); _seed_canonical(db); _seed_sources(db)
    future = datetime.now(timezone.utc) + timedelta(hours=10)
    out = build_reconciliation_report(db, "P603", now=future)
    assert out["integration_slo"]["freshness_compliance"] == 0.0
    assert out["pilot_acceptance"]["status"] == "NOT_READY"
    assert any(x["code"] == "FRESHNESS_COMPLIANCE" for x in out["pilot_acceptance"]["blockers"])


def test_canonical_mapping_target_validation_is_project_scoped():
    db = _db(); _seed_canonical(db)
    assert canonical_target_exists(db, "P603", "part", "P1") is True
    assert canonical_target_exists(db, "P603", "part", "NOPE") is False
    assert canonical_target_exists(db, "P603", "vin", "VIN001") is True


def test_report_is_read_only_and_never_claims_automatic_conflict_resolution():
    db = _db(); _seed_canonical(db); _seed_sources(db)
    out = build_reconciliation_report(db, "P603")
    assert out["governance"]["read_only_reconciliation"] is True
    assert out["governance"]["no_automatic_source_system_write"] is True
    assert out["governance"]["no_automatic_mapping_confirmation"] is True
    assert out["source_of_truth_conflicts"]["no_automatic_winner_selection"] is True


def test_confirmed_alias_mapping_is_applied_to_reconciliation_copy_only():
    db = _db(); _seed_canonical(db)
    plm = _system(db, "plm-map", "plm", "ebom")
    erp = _system(db, "erp-map", "erp", "mbom")
    p = _obj(db, plm, "E-A", "ebom_item", {"parent_part_number": "ROOT", "child_part_number": "P_ALIAS", "child_revision": "D", "quantity": 1, "position": "10"})
    _obj(db, erp, "M-A", "mbom_item", {"parent_part_number": "ROOT", "child_part_number": "P1", "child_revision": "D", "quantity": 1, "position": "10"})
    db.add(IntegrationEntityMapping(system_id=plm.id, project_code="P603", source_entity_type="part", source_external_id=p.external_id, source_key="P_ALIAS", canonical_entity_type="part", canonical_key="P1", status="confirmed", source_fingerprint=p.source_fingerprint))
    db.commit()
    out = build_reconciliation_report(db, "P603", policy={"required_roles": ["ebom", "mbom"], "min_mapping_coverage": 1.0, "min_freshness_compliance": 0.0, "min_sync_success_rate": 0.0})
    assert out["ebom_vs_mbom"]["status"] == "MATCH"
    original = db.scalar(select(ExternalObject).where(ExternalObject.system_id == plm.id, ExternalObject.external_id == "E-A"))
    assert original.metadata_json["child_part_number"] == "P_ALIAS"
