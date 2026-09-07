from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    AsBuiltConfiguration, BOMItem, ChangeCutIn, ConfigurationApplicability, ConfigurationEffectivity,
    Document, DocumentStatus, EngineeringDeviation, ManufacturingBOMItem, Part, Project, ProjectArea,
    VehicleVariant, ReleaseBaseline,
)
from app.db.session import Base
from app.services.configuration_release_assurance import (
    configuration_release_assurance_workspace, visible_assurance_rows,
)
from app.services.release_baseline import build_release_snapshot


def _db():
    engine=create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _seed(db: Session, code="CRA55"):
    project=Project(code=code,name="Configuration Assurance",root_part_number=f"ROOT-{code}",acl_groups=["engineering-ai-users"])
    area=ProjectArea(project_code=code,code="assembly",name="Сборка",acl_groups=["engineering-ai-users"])
    root=Part(part_number=f"ROOT-{code}",name="Vehicle",project_code=code,latest_revision="A",metadata_json={"manufacturing_area":"assembly"})
    child=Part(part_number=f"PART-{code}",name="Bracket",project_code=code,latest_revision="D",metadata_json={"manufacturing_area":"assembly"})
    ebom_doc=Document(filename="ebom.csv",stored_path="/tmp/ebom.csv",sha256="a"*64,status=DocumentStatus.ready,part_number=root.part_number,revision="A",doc_type="bom",project_code=code,manufacturing_area="assembly",acl_groups=["engineering-ai-users"])
    ev=Document(filename="evidence.pdf",stored_path="/tmp/evidence.pdf",sha256="b"*64,status=DocumentStatus.ready,part_number=child.part_number,revision="D",doc_type="drawing",project_code=code,manufacturing_area="assembly",acl_groups=["engineering-ai-users"])
    db.add_all([project,area,root,child,ebom_doc,ev]);db.commit();db.refresh(ebom_doc);db.refresh(ev)
    db.add(BOMItem(parent_part_number=root.part_number,parent_revision="A",child_part_number=child.part_number,child_revision="D",quantity=1,unit="pcs",position="10",source_document_id=ebom_doc.id))
    v=VehicleVariant(project_code=code,manufacturing_area="assembly",code="PREMIUM",name="Premium",status="released",market="RU",trim="Premium",evidence_document_ids=[ev.id])
    db.add(v);db.commit();db.refresh(v)
    for pn in (root.part_number,child.part_number):
        db.add(ConfigurationApplicability(project_code=code,variant_id=v.id,manufacturing_area="assembly",entity_type="part",entity_key=pn,applicability="included",source="manual",evidence_document_ids=[ev.id]))
    db.commit()
    return project,root,child,ebom_doc,ev,v


def _workspace(db,project,root,child,ebom_doc,ev,v):
    return configuration_release_assurance_workspace(db,project,{ebom_doc.id,ev.id},{root.part_number,child.part_number},"assembly",{"assembly"},v.id,None)


def test_ebom_mbom_reconciliation_and_exact_100_percent_configuration():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db)
    db.add(ManufacturingBOMItem(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,parent_part_number=root.part_number,parent_revision="A",child_part_number=child.part_number,child_revision="D",quantity=1,unit="pcs",position="10",source_system="erp",evidence_document_ids=[ev.id]))
    db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["configuration"]["exact_100_percent"] is True
    assert out["ebom_mbom"]["status"] == "ALIGNED"
    assert out["ebom_mbom"]["summary"] == {"missing_in_mbom":0,"extra_in_mbom":0,"changed":0}


def test_revision_mismatch_is_blocking_buildability_signal():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"MISMATCH55")
    db.add(ManufacturingBOMItem(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,parent_part_number=root.part_number,child_part_number=child.part_number,child_revision="C",quantity=1,unit="pcs",position="10",source_system="erp",evidence_document_ids=[ev.id]))
    db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["ebom_mbom"]["status"] == "MISMATCH"
    assert out["ebom_mbom"]["summary"]["changed"] == 1
    assert out["buildability"]["status"] == "RED"
    assert any(x["type"]=="ebom_mbom_mismatch" for x in out["buildability"]["blockers"])


def test_unknown_variant_applicability_is_never_silently_included():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"UNKNOWN55")
    row=db.query(ConfigurationApplicability).filter_by(project_code=project.code,entity_key=child.part_number).one();db.delete(row);db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert child.part_number in out["configuration"]["unknown_parts"]
    assert out["configuration"]["unknown_is_not_included"] is True
    assert any(x["type"]=="unknown_applicability" for x in out["buildability"]["blockers"])


def test_effectivity_detects_as_built_revision_mismatch_and_honors_approved_deviation():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"BUILT55")
    eff=ConfigurationEffectivity(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,part_number=child.part_number,revision="D",plant="Kaluga",vin_from="X000100",status="active",source="plm",evidence_document_ids=[ev.id])
    built=AsBuiltConfiguration(project_code=project.code,manufacturing_area="assembly",vehicle_identifier="X000150",variant_id=v.id,plant="Kaluga",part_number=child.part_number,revision="C",source_system="mes",evidence_document_ids=[ev.id])
    db.add_all([eff,built]);db.commit();db.refresh(built)
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["as_built"]["status"] == "RED"
    assert out["as_built"]["mismatches"][0]["authorized_deviation"] is False
    dev=EngineeringDeviation(project_code=project.code,manufacturing_area="assembly",code="DEV-55",part_number=child.part_number,released_revision="D",requested_revision="C",reason="controlled stock use",status="approved",evidence_document_ids=[ev.id])
    db.add(dev);db.commit();db.refresh(dev);built.deviation_id=dev.id;db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["as_built"]["status"] == "AMBER"
    assert out["as_built"]["mismatches"][0]["authorized_deviation"] is True


def test_cutin_requires_stock_disposition_logistics_and_ppap():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"CUT55")
    db.add(ChangeCutIn(project_code=project.code,manufacturing_area="assembly",code="CUT-55",part_number=child.part_number,from_revision="C",to_revision="D",variant_ids=[v.id],plant="Kaluga",cut_in_at=datetime.now(timezone.utc)+timedelta(days=2),old_stock_qty=1200,logistics_confirmed=False,status="planned",evidence_document_ids=[ev.id]))
    db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    cut=out["change_cutins"][0]
    assert cut["readiness"] == "BLOCKED"
    assert "old_stock_disposition_missing" in cut["gaps"]
    assert "logistics_cutover_not_confirmed" in cut["gaps"]
    assert "ppap_for_new_revision_not_approved" in cut["gaps"]


def test_mixed_hidden_evidence_fails_closed_for_configuration_authority_rows():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"ACL55")
    hidden=Document(filename="hidden.pdf",stored_path="/tmp/hidden.pdf",sha256="c"*64,status=DocumentStatus.ready,part_number=child.part_number,revision="D",doc_type="spec",project_code=project.code,manufacturing_area="assembly",acl_groups=["secret"])
    db.add(hidden);db.commit();db.refresh(hidden)
    db.add(ManufacturingBOMItem(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,parent_part_number=root.part_number,child_part_number=child.part_number,child_revision="D",position="10",source_system="erp",evidence_document_ids=[ev.id,hidden.id]))
    db.commit()
    rows=visible_assurance_rows(db,project.code,{ebom_doc.id,ev.id},{root.part_number,child.part_number},"assembly",{"assembly"})
    assert rows["mbom"] == []


def test_release_package_is_fingerprinted_and_never_auto_approves_release():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"PACK55")
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    pkg=out["release_package"]
    assert len(pkg["fingerprint"]) == 64
    assert pkg["human_release_approval_required"] is True
    assert out["governance"]["no_automatic_release"] is True


def test_variant_plant_matrix_and_cross_system_consistency_are_explainable():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"MATRIX55")
    db.add(ConfigurationEffectivity(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,part_number=child.part_number,revision="D",plant="Kaluga",status="active",source="plm",evidence_document_ids=[ev.id]))
    db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["variant_plant_matrix"]
    assert out["variant_plant_matrix"][0]["variant_code"] == "PREMIUM"
    assert out["system_consistency"]["read_only"] is True
    assert out["system_consistency"]["no_automatic_source_system_write"] is True


def test_ask_configuration_is_deterministic_and_cpu_only():
    from app.services.configuration_release_assurance import configuration_assurance_answer
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"ASK55")
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    ans=configuration_assurance_answer(out,"Почему Premium нельзя передать на Pilot Build?")
    assert ans["deterministic"] is True
    assert ans["llm_required"] is False
    assert "Configuration assurance" in ans["answer"]


def test_release_drift_ignores_capture_timestamp_and_lifecycle_views_are_explicit():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"DRIFT55")
    snap, candidate, warnings=build_release_snapshot(db,project,{ebom_doc.id,ev.id},{root.part_number,child.part_number},{"assembly"},v.id,"assembly")
    base=ReleaseBaseline(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,code="REL-55",name="Release 55",baseline_type="release",root_part_number=root.part_number,status="frozen",snapshot_json=snap,fingerprint="f"*64,source_document_ids=[ebom_doc.id,ev.id],release_candidate=candidate,created_by="tester")
    db.add(base);db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["release_drift"]["status"] == "MATCH"
    assert out["manufacturing_handover"]["human_approval_required"] is True
    assert out["as_designed_planned_built"]["as_designed"]["source"].startswith("PLM/PDM")
    assert out["as_designed_planned_built"]["as_planned"]["source"].startswith("ERP")
    assert out["as_designed_planned_built"]["as_built"]["source"].startswith("MES")


def test_release_drift_detects_mbom_change_after_freeze():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"MBOMDRIFT55")
    row=ManufacturingBOMItem(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,parent_part_number=root.part_number,parent_revision="A",child_part_number=child.part_number,child_revision="D",quantity=1,unit="pcs",position="10",source_system="erp",evidence_document_ids=[ev.id])
    db.add(row);db.commit();db.refresh(row)
    snap,candidate,_=build_release_snapshot(db,project,{ebom_doc.id,ev.id},{root.part_number,child.part_number},{"assembly"},v.id,"assembly")
    assert snap["manufacturing_bom"] and snap["schema"] == "mgc-release-baseline-v3"
    base=ReleaseBaseline(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,code="REL-MBOM-55",name="MBOM Freeze",baseline_type="release",root_part_number=root.part_number,status="frozen",snapshot_json=snap,fingerprint="e"*64,source_document_ids=[ebom_doc.id,ev.id],release_candidate=candidate,created_by="tester")
    db.add(base);db.commit()
    assert _workspace(db,project,root,child,ebom_doc,ev,v)["release_drift"]["status"] == "MATCH"
    row.child_revision="C";db.commit()
    drift=_workspace(db,project,root,child,ebom_doc,ev,v)["release_drift"]
    assert drift["status"] == "DRIFT" and drift["drift"] is True


def test_as_built_effectivity_uses_vin_scope_not_all_active_revisions():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"VIN55")
    db.add_all([
        ConfigurationEffectivity(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,part_number=child.part_number,revision="C",plant="Kaluga",vin_to="X000099",status="active",source="plm",evidence_document_ids=[ev.id]),
        ConfigurationEffectivity(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,part_number=child.part_number,revision="D",plant="Kaluga",vin_from="X000100",status="active",source="plm",evidence_document_ids=[ev.id]),
        AsBuiltConfiguration(project_code=project.code,manufacturing_area="assembly",vehicle_identifier="X000150",variant_id=v.id,plant="Kaluga",part_number=child.part_number,revision="D",source_system="mes",evidence_document_ids=[ev.id]),
    ]);db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["as_built"]["status"] == "GREEN"
    built=db.query(AsBuiltConfiguration).filter_by(project_code=project.code).one(); built.revision="C"; db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["as_built"]["status"] == "RED"
    assert out["as_built"]["mismatches"][0]["expected_revisions"] == ["D"]


def test_configuration_release_package_fingerprint_includes_mbom_and_effectivity():
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"PKG255")
    mb=ManufacturingBOMItem(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,parent_part_number=root.part_number,child_part_number=child.part_number,child_revision="D",quantity=1,unit="pcs",position="10",source_system="erp",evidence_document_ids=[ev.id])
    eff=ConfigurationEffectivity(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,part_number=child.part_number,revision="D",plant="Kaluga",vin_from="X000100",status="active",source="plm",evidence_document_ids=[ev.id])
    db.add_all([mb,eff]);db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v); fp1=out["release_package"]["fingerprint"]
    mb.child_revision="E";db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v); fp2=out["release_package"]["fingerprint"]
    assert fp1 != fp2
    assert out["release_package"]["schema"] == "mgc-configuration-release-package-v2"
    assert out["release_package"]["counts"]["manufacturing_bom_items"] == 1


def test_release_baseline_v3_freezes_manufacturing_configuration_and_detects_drift():
    from app.services.release_baseline import create_release_baseline
    db=_db();project,root,child,ebom_doc,ev,v=_seed(db,"BASE55")
    mb=ManufacturingBOMItem(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,parent_part_number=root.part_number,child_part_number=child.part_number,child_revision="D",quantity=1,unit="pcs",position="10",source_system="erp",evidence_document_ids=[ev.id])
    eff=ConfigurationEffectivity(project_code=project.code,manufacturing_area="assembly",variant_id=v.id,part_number=child.part_number,revision="D",plant="Kaluga",status="active",source="plm",evidence_document_ids=[ev.id])
    db.add_all([mb,eff]);db.commit()
    base=create_release_baseline(db,project,code="REL55",name="Release 55",baseline_type="release",created_by="admin",visible_document_ids={ebom_doc.id,ev.id},visible_part_numbers={root.part_number,child.part_number},allowed_area_codes={"assembly"},variant_id=v.id,manufacturing_area="assembly")
    assert base.snapshot_json["schema"] == "mgc-release-baseline-v3"
    assert len(base.snapshot_json["manufacturing_bom"]) == 1
    assert len(base.snapshot_json["configuration_effectivity"]) == 1
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["release_drift"]["status"] == "MATCH"
    mb.child_revision="E";db.commit()
    out=_workspace(db,project,root,child,ebom_doc,ev,v)
    assert out["release_drift"]["status"] == "DRIFT"
